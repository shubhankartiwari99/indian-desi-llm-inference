#-*- coding: utf-8 -*-

class VoiceError(Exception):
    """Base class for voice exceptions."""
    pass

class VoiceContractError(VoiceError):
    """Exception for voice contract violations."""
    pass

class VoiceSelectionError(VoiceError):
    """Exception for voice selection errors."""
    pass

class VoiceStateError(VoiceError):
    """Exception for voice state errors."""
    pass

class VoiceAssemblyError(VoiceError):
    """Exception for voice assembly errors."""
    pass
