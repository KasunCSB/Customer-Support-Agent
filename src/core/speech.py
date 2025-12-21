"""
Azure Speech Services Module

Provides speech-to-text (STT) and text-to-speech (TTS) functionality
using Azure Cognitive Services Speech SDK.

Usage:
    from src.core.speech import SpeechService
    
    service = SpeechService()
    
    # Speech-to-text
    text = service.recognize_from_microphone()
    
    # Text-to-speech
    service.speak("Hello, how can I help you?")
"""

import azure.cognitiveservices.speech as speechsdk
from typing import Optional, Callable
from src.config import settings
from src.logger import get_logger

logger = get_logger(__name__)


class SpeechService:
    """
    Azure Speech Services wrapper for STT and TTS.
    
    Provides a clean interface for:
    - Recognizing speech from microphone
    - Synthesizing speech from text
    - Handling recognition events and errors
    """
    
    def __init__(self):
        """Initialize speech service with Azure credentials."""
        if not settings.speech.is_configured:
            raise ValueError(
                "Azure Speech not configured. Set AZURE_SPEECH_API_KEY and "
                "AZURE_SPEECH_REGION in your .env file."
            )
        
        # Create speech config
        self._speech_config = speechsdk.SpeechConfig(
            subscription=settings.speech.api_key,
            region=settings.speech.region
        )
        
        # Set speech recognition language
        self._speech_config.speech_recognition_language = settings.speech.language
        
        # Set TTS voice
        self._speech_config.speech_synthesis_voice_name = settings.speech.voice_name
        
        # Create audio configs
        self._audio_input_config = speechsdk.audio.AudioConfig(
            use_default_microphone=True
        )
        self._audio_output_config = speechsdk.audio.AudioOutputConfig(
            use_default_speaker=True
        )
        
        logger.info(
            f"Speech service initialized: region={settings.speech.region}, "
            f"language={settings.speech.language}, voice={settings.speech.voice_name}"
        )
    
    def recognize_from_microphone(
        self,
        timeout: Optional[float] = None,
        on_recognizing: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """
        Recognize speech from the default microphone.
        
        Args:
            timeout: Maximum seconds to wait for speech (uses config default if None)
            on_recognizing: Optional callback for interim results
            
        Returns:
            Recognized text, or None if recognition failed/timed out
        """
        timeout = timeout or settings.speech.speech_timeout
        
        # Create recognizer
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self._speech_config,
            audio_config=self._audio_input_config
        )
        
        # Set up interim results callback if provided
        if on_recognizing:
            def recognizing_handler(evt):
                if evt.result.text:
                    on_recognizing(evt.result.text)
            recognizer.recognizing.connect(recognizing_handler)
        
        logger.debug("Listening for speech...")
        
        # Perform recognition
        result = recognizer.recognize_once_async().get()
        
        # Handle result
        if result is None:
            logger.warning("Recognition returned no result")
            return None
        
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            logger.debug(f"Recognized: {result.text}")
            return result.text
        
        elif result.reason == speechsdk.ResultReason.NoMatch:
            details = result.no_match_details
            logger.debug(f"No speech recognized: {details.reason}")
            return None
        
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            logger.warning(f"Recognition canceled: {cancellation.reason}")
            if cancellation.reason == speechsdk.CancellationReason.Error:
                logger.error(f"Error details: {cancellation.error_details}")
            return None
        
        return None
    
    def speak(
        self,
        text: str,
        on_started: Optional[Callable[[], None]] = None,
        on_completed: Optional[Callable[[], None]] = None
    ) -> bool:
        """
        Synthesize speech from text using Azure TTS.
        
        Args:
            text: Text to speak
            on_started: Optional callback when speech starts
            on_completed: Optional callback when speech completes
            
        Returns:
            True if synthesis succeeded, False otherwise
        """
        if not text:
            return False
        
        # Create synthesizer
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self._speech_config,
            audio_config=self._audio_output_config
        )
        
        # Set up callbacks
        if on_started:
            synthesizer.synthesis_started.connect(lambda evt: on_started())
        if on_completed:
            synthesizer.synthesis_completed.connect(lambda evt: on_completed())
        
        logger.debug(f"Speaking: {text[:50]}...")
        
        # Perform synthesis
        result = synthesizer.speak_text_async(text).get()
        
        # Handle result
        if result is None:
            logger.warning("Synthesis returned no result")
            return False
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logger.debug("Speech synthesis completed")
            return True
        
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            logger.warning(f"Synthesis canceled: {cancellation.reason}")
            if cancellation.reason == speechsdk.CancellationReason.Error:
                logger.error(f"Error details: {cancellation.error_details}")
            return False
        
        return False
    
    def speak_ssml(self, ssml: str) -> bool:
        """
        Synthesize speech from SSML markup.
        
        Args:
            ssml: SSML formatted text
            
        Returns:
            True if synthesis succeeded, False otherwise
        """
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self._speech_config,
            audio_config=self._audio_output_config
        )
        
        result = synthesizer.speak_ssml_async(ssml).get()
        
        if result is None:
            return False
        
        return result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted

