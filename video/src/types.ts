export type Cue = {
  module: string;
  target: string;
  reason: string;
  pattern?: MotionPatternId;
  patternSource?: 'auto' | 'explicit';
  patternReasons?: string[];
  patternWarnings?: string[];
  step: number;
  atFrame: number;
  durationFrames: number;
};

export type MotionPatternId =
  | 'kinetic-type'
  | 'flat-shape'
  | 'info-motion'
  | 'ui-motion'
  | 'card-stack-3d'
  | 'particle-warp'
  | 'glitch'
  | 'liquid-morph'
  | 'isometric-build'
  | 'paper-cut'
  | 'type-mask'
  | 'environment-type'
  | 'occlusion'
  | 'scramble-decode'
  | 'variable-font'
  | 'swiss-grid'
  | 'extruded-type'
  | 'street-collage'
  | 'path-drawing';

export type Block = {
  id: string;
  module: string;
  slot?: string;
  data: Record<string, unknown>;
};

export type DesignTokens = {
  paletteId: string;
  datavizId: string;
  typographyId: string;
  palette: Record<string, string>;
  dataviz: Record<string, string>;
};

export type Scene = {
  id: string;
  index: number;
  title: string;
  summary: string;
  communicationGoal: string;
  intent: string;
  layout: string;
  theme: string;
  blocks: Block[];
  slots: Record<string, string[]>;
  cues: Cue[];
  startFrame: number;
  durationFrames: number;
  transitionFrames: number;
};

export type Storyboard = {
  schemaVersion: 1;
  source: 'html-slide';
  title: string;
  language: 'ko' | 'en';
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  design: DesignTokens;
  scenes: Scene[];
};
