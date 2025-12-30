/**
 * Audio Player with Multilingual TTS Support
 * Uses ElevenLabs API for text-to-speech
 */

const ELEVENLABS_API_KEY = process.env.NEXT_PUBLIC_ELEVENLABS_API_KEY;
const ELEVENLABS_API_URL = 'https://api.elevenlabs.io/v1/text-to-speech';

export class AudioPlayer {
  private audio: HTMLAudioElement | null = null;
  private currentBlobUrl: string | null = null;
  public isPlaying: boolean = false;

  /**
   * Play text with TTS
   * @param text Text to speak
   * @param voiceId ElevenLabs voice ID (default: multilingual voice)
   */
  async playText(text: string, voiceId: string = 'pNInz6obpgDQGcFmaJgB'): Promise<void> {
    try {
      // Clean up previous audio
      this.stop();

      // Call Backend Voice Proxy
      // We use the proxy instead of direct ElevenLabs to hide keys and simplify frontend
      const formData = new FormData();
      formData.append('text', text);
      formData.append('voice_id', voiceId);

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/voice/synthesize`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`TTS failed: ${response.statusText}`);
      }

      // Get audio blob
      const audioBlob = await response.blob();
      this.currentBlobUrl = URL.createObjectURL(audioBlob);

      // Create and play audio
      this.audio = new Audio(this.currentBlobUrl);
      this.audio.onplay = () => { this.isPlaying = true; };
      this.audio.onended = () => { this.isPlaying = false; this.cleanup(); };
      this.audio.onerror = () => { this.isPlaying = false; this.cleanup(); };

      await this.audio.play();
    } catch (error) {
      console.error('TTS playback failed:', error);
      this.isPlaying = false;

      const errorMsg = error instanceof Error ? error.message : 'TTS Failed';
      if (errorMsg.includes('401') || errorMsg.includes('Unusual activity')) {
        // Use a dynamic import or global trigger if toast isn't available here, 
        // BUT since this is a class, we might need to rely on the caller or just console error + alert
        // For now, let's reconfirm the error is thrown so ChatScreen can catch it?
        // ChatScreen calls `apiClient.sendMessage` -> `addMessage` -> `audioPlayer.playText`
        // handleSendMessage catches errors! 
        throw new Error("Voice Service Unavailable: Check API Key");
      }
      throw error;
    }
  }

  /**
   * Pause playback
   */
  pause(): void {
    if (this.audio && !this.audio.paused) {
      this.audio.pause();
      this.isPlaying = false;
    }
  }

  /**
   * Resume playback
   */
  resume(): void {
    if (this.audio && this.audio.paused) {
      this.audio.play();
      this.isPlaying = true;
    }
  }

  /**
   * Stop playback and cleanup
   */
  stop(): void {
    if (this.audio) {
      this.audio.pause();
      this.audio.currentTime = 0;
    }
    this.isPlaying = false;
    this.cleanup();
  }

  /**
   * Cleanup resources
   */
  private cleanup(): void {
    if (this.currentBlobUrl) {
      URL.revokeObjectURL(this.currentBlobUrl);
      this.currentBlobUrl = null;
    }
    this.audio = null;
  }
}

// Singleton instance
export const audioPlayer = new AudioPlayer();
