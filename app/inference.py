import torch
from app.model_loader import ModelLoader
from app.scaffolds import get_response_scaffold
from app.utils import normalize_output
from app.policies import apply_response_policies
from app.language import detect_language
from app.prompt_builder import build_prompt
from app.intent import detect_intent
from app.conversation import ConversationMemory
from app.retriever import KnowledgeRetriever
from app.facts import resolve_fact
from app.topic_policy import INTENT_TO_TOPICS
from app.policies import EMOTIONAL_FALLBACK


class InferenceEngine:
    def __init__(self, model_dir=None, lora_dir="artifacts/lora_adapter"):
        loader = ModelLoader(
            model_dir=model_dir,
            lora_dir=lora_dir
        )
        self.model, self.tokenizer, self.device = loader.load()
        self.retriever = KnowledgeRetriever()
        self.memory = ConversationMemory(max_turns=4)

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 128,
        mode: str = "auto"
    ) -> str:

        if not prompt or not prompt.strip():
            raise ValueError("Prompt must be non-empty")

        intent = detect_intent(prompt)
        lang = detect_language(prompt)

        fact = resolve_fact(prompt, lang)
        if fact and fact.get("confidence") == "high":
            answer = fact["answer"]
            self.memory.add_user(prompt)
            self.memory.add_assistant(answer)
            return answer

        if intent == "emotional":
            aligned_prompt = build_prompt(
                prompt=prompt,
                lang=lang,
                intent="emotional",
                facts=None
            )

            inputs = self.tokenizer(
                aligned_prompt,
                return_tensors="pt",
                truncation=True,
                max_length=256
            ).to(self.device)

            generation_args = {
                "input_ids": inputs["input_ids"],
                "attention_mask": inputs["attention_mask"],
                "max_new_tokens": min(max_new_tokens, 80),
                "do_sample": True,
                "temperature": 0.7,
                "top_p": 0.95,
                "repetition_penalty": 1.05,
                "no_repeat_ngram_size": 2,
                "pad_token_id": self.tokenizer.eos_token_id,
            }

            with torch.no_grad():
                outputs = self.model.generate(**generation_args)

            raw = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            normalized = normalize_output(raw)

            scaffold = get_response_scaffold("emotional", lang)
            
            if normalized:
                response_text = scaffold + normalized
            else:
                response_text = EMOTIONAL_FALLBACK.get(lang, EMOTIONAL_FALLBACK["en"])

            self.memory.add_user(prompt)
            self.memory.add_assistant(response_text)

            return apply_response_policies(
                response_text,
                intent="emotional",
                lang=lang
                )

        memory_block = ""
        if intent in {"conversational", "explanatory"} and not self.memory.is_empty():
            memory_block = (
                "Conversation so far:\n"
                f"{self.memory.render()}\n\n"
            )

        retrieved = None
        facts = None

        if intent in {"factual", "explanatory"}:
            retrieved = self.retriever.retrieve(prompt, lang)

            if retrieved:
                confidence = retrieved.get("confidence")
                topic = retrieved.get("topic")

                allowed_topics = INTENT_TO_TOPICS.get(intent, set())

                # HIGH confidence → direct answer
                if confidence == "high" and topic in allowed_topics:
                    answer = retrieved["fact"]
                    self.memory.add_user(prompt)
                    self.memory.add_assistant(answer)
                    return answer

                # MEDIUM confidence → inject into prompt only
                if confidence == "medium" and topic in allowed_topics:
                    facts = retrieved["fact"]

        aligned_prompt = (
            memory_block +
            build_prompt(prompt, lang, intent, facts)
        )

        inputs = self.tokenizer(
            aligned_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=256
        ).to(self.device)

        generation_args = {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"],
            "max_new_tokens": max_new_tokens,
            "pad_token_id": self.tokenizer.eos_token_id,
        }

        if intent == "factual":
            generation_args.update({
                "do_sample": False,
                "num_beams": 1,
                "early_stopping": True,
            })

        elif intent == "explanatory":
            generation_args.update({
                "do_sample": True,
                "temperature": 0.6,
                "top_p": 0.9,
                "repetition_penalty": 1.1,
                "no_repeat_ngram_size": 3,
            })

        else:  # conversational
            generation_args.update({
                "do_sample": True,
                "temperature": 0.65,
                "top_p": 0.92,
                "repetition_penalty": 1.1,
                "no_repeat_ngram_size": 3,
            })

        with torch.no_grad():
            outputs = self.model.generate(**generation_args)

        raw = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        normalized = normalize_output(raw)

        scaffold = get_response_scaffold(intent, lang)
        response_text = scaffold + normalized if normalized else scaffold

        self.memory.add_user(prompt)
        self.memory.add_assistant(response_text)

        return apply_response_policies(
            response_text,
            intent=intent,
            lang=lang
            )