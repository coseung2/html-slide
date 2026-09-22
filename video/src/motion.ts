import {Easing, interpolate} from 'remotion';
import type {Cue, Scene} from './types';

export const cuesFor = (
  scene: Scene,
  target: string,
  module?: string
): Cue[] => scene.cues.filter(
  (cue) => cue.target === target && (!module || cue.module === module)
);

export const hasCue = (
  scene: Scene,
  target: string,
  module?: string
): boolean => cuesFor(scene, target, module).length > 0;

const completion = (cue: Cue, frame: number): number => {
  if (frame < cue.atFrame) return 0;
  if (cue.durationFrames <= 1) return 1;
  return interpolate(
    frame,
    [cue.atFrame, cue.atFrame + cue.durationFrames],
    [0, 1],
    {
      easing: Easing.out(Easing.cubic),
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp'
    }
  );
};

export const cueCompletion = (
  scene: Scene,
  target: string,
  module: string,
  frame: number
): number => {
  const cues = cuesFor(scene, target, module);
  if (!cues.length) return 1;
  return Math.max(...cues.map((cue) => completion(cue, frame)));
};

export const cuePulse = (
  scene: Scene,
  target: string,
  module: string,
  frame: number
): number => {
  const cue = cuesFor(scene, target, module).find(
    (item) => frame >= item.atFrame && frame <= item.atFrame + item.durationFrames
  );
  if (!cue) return 0;
  if (cue.durationFrames <= 1) return 1;
  const middle = cue.atFrame + cue.durationFrames / 2;
  return interpolate(
    frame,
    [cue.atFrame, middle, cue.atFrame + cue.durationFrames],
    [0, 1, 0],
    {
      easing: Easing.inOut(Easing.ease),
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp'
    }
  );
};

export const sequenceItemProgress = (
  scene: Scene,
  target: string,
  index: number,
  frame: number
): number => {
  const cues = cuesFor(scene, target, 'sequence-step');
  if (!cues.length) return 1;
  const cue = cues.find((item) => item.step === index + 1);
  return cue ? completion(cue, frame) : 1;
};
