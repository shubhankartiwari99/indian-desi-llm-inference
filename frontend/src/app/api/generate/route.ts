import { NextResponse } from 'next/server';

const ENDPOINT = "https://michal-unboarded-erna.ngrok-free.dev/generate";

export async function POST(req: Request) {
    try {
        const body = await req.json();

        // Create an abort controller to set a 180s timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 180000);

        const response = await fetch(ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error: unknown) {
        console.error("Inference Error:", error);
        return NextResponse.json({ error: (error as Error).message }, { status: 500 });
    }
}
