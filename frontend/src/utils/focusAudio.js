// Gerador de Áudio de Concentração e Ruído Branco via Web Audio API nativa
// Funciona 100% offline, sintetizado em tempo real com pureza estéreo

class FocusAudioService {
  constructor() {
    this.ctx = null;
    this.currentSource = null;
    this.gainNode = null;
    this.currentType = "none";
    this.volume = 0.35;
  }

  _initContext() {
    if (!this.ctx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioContextClass();
    }
    if (this.ctx.state === "suspended") {
      this.ctx.resume();
    }
  }

  stop() {
    if (this.currentSource) {
      try {
        if (typeof this.currentSource.stop === "function") {
          this.currentSource.stop();
        } else if (Array.isArray(this.currentSource)) {
          this.currentSource.forEach((s) => s.stop && s.stop());
        }
        if (this.currentSource.disconnect) {
          this.currentSource.disconnect();
        }
      } catch {
        /* ignora */
      }
      this.currentSource = null;
    }
    this.currentType = "none";
  }

  setVolume(val) {
    this.volume = Math.max(0, Math.min(1, val));
    if (this.gainNode && this.ctx) {
      this.gainNode.gain.setValueAtTime(this.volume, this.ctx.currentTime);
    }
  }

  play(type = "brown", volume = this.volume) {
    this.stop();
    if (type === "none") return;

    this._initContext();
    this.volume = volume;

    this.gainNode = this.ctx.createGain();
    this.gainNode.gain.setValueAtTime(this.volume, this.ctx.currentTime);
    this.gainNode.connect(this.ctx.destination);

    this.currentType = type;

    if (type === "white") {
      this._playWhiteNoise();
    } else if (type === "brown") {
      this._playBrownNoise();
    } else if (type === "binaural") {
      this._playBinauralBeats();
    }
  }

  _playWhiteNoise() {
    const bufferSize = 2 * this.ctx.sampleRate;
    const noiseBuffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const output = noiseBuffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      output[i] = Math.random() * 2 - 1;
    }

    const whiteNoise = this.ctx.createBufferSource();
    whiteNoise.buffer = noiseBuffer;
    whiteNoise.loop = true;

    // Filtro passa-baixa suave para não soar agressivo nos ouvidos
    const filter = this.ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(8000, this.ctx.currentTime);

    whiteNoise.connect(filter);
    filter.connect(this.gainNode);
    whiteNoise.start(0);

    this.currentSource = whiteNoise;
  }

  _playBrownNoise() {
    // Ruído marrom: gera sensação profunda de chuva constante / cachoeira distante
    const bufferSize = 2 * this.ctx.sampleRate;
    const noiseBuffer = this.ctx.createBuffer(2, bufferSize, this.ctx.sampleRate);
    const left = noiseBuffer.getChannelData(0);
    const right = noiseBuffer.getChannelData(1);

    let lastLeft = 0.0;
    let lastRight = 0.0;
    for (let i = 0; i < bufferSize; i++) {
      const whiteL = Math.random() * 2 - 1;
      const whiteR = Math.random() * 2 - 1;
      lastLeft = (lastLeft + 0.02 * whiteL) / 1.02;
      lastRight = (lastRight + 0.02 * whiteR) / 1.02;
      left[i] = lastLeft * 3.5;
      right[i] = lastRight * 3.5;
    }

    const brownNoise = this.ctx.createBufferSource();
    brownNoise.buffer = noiseBuffer;
    brownNoise.loop = true;

    // Filtro sutil para simular som natural
    const filter = this.ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(1200, this.ctx.currentTime);

    brownNoise.connect(filter);
    filter.connect(this.gainNode);
    brownNoise.start(0);

    this.currentSource = brownNoise;
  }

  _playBinauralBeats() {
    // Tom binaural 40Hz (Foco e Sincronização Cognitiva)
    // Canal esquerdo: 200 Hz | Canal direito: 240 Hz
    const merger = this.ctx.createChannelMerger(2);

    const oscLeft = this.ctx.createOscillator();
    oscLeft.type = "sine";
    oscLeft.frequency.setValueAtTime(200, this.ctx.currentTime);

    const oscRight = this.ctx.createOscillator();
    oscRight.type = "sine";
    oscRight.frequency.setValueAtTime(240, this.ctx.currentTime);

    oscLeft.connect(merger, 0, 0);
    oscRight.connect(merger, 0, 1);

    merger.connect(this.gainNode);

    oscLeft.start(0);
    oscRight.start(0);

    this.currentSource = [oscLeft, oscRight];
  }
}

export const focusAudio = new FocusAudioService();
