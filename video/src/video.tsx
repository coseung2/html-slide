import React from 'react';
import {
  AbsoluteFill,
  Easing,
  interpolate,
  Sequence,
  useCurrentFrame
} from 'remotion';

export type Cue = {
  module: string;
  target: string;
  reason: string;
  atFrame: number;
  durationFrames: number;
};

export type Block = {
  id: string;
  module: string;
  slot?: string;
  data: Record<string, unknown>;
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
  style: Record<string, unknown>;
  blocks: Block[];
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
  scenes: Scene[];
};

const valueText = (value: unknown): string => {
  if (typeof value === 'string' || typeof value === 'number') return String(value);
  if (Array.isArray(value)) {
    return value
      .slice(0, 8)
      .map((item) => typeof item === 'object' ? JSON.stringify(item) : String(item))
      .join(' · ');
  }
  if (value && typeof value === 'object') return JSON.stringify(value);
  return '';
};

const blockText = (block: Block): string => {
  const data = block.data;
  const preferred = ['text', 'value', 'label', 'quote', 'items', 'left', 'right'];
  const parts = preferred
    .filter((key) => key in data)
    .map((key) => valueText(data[key]))
    .filter(Boolean);
  return parts.length ? parts.join('\n') : JSON.stringify(data);
};

const cueFor = (scene: Scene, blockId: string, localFrame: number) => {
  return scene.cues.find((cue) =>
    cue.target === blockId &&
    localFrame >= cue.atFrame &&
    localFrame < cue.atFrame + cue.durationFrames
  );
};

const BlockCard: React.FC<{block: Block; scene: Scene; localFrame: number}> = ({
  block,
  scene,
  localFrame
}) => {
  const cue = cueFor(scene, block.id, localFrame);
  let emphasis = 0;
  if (cue) {
    emphasis = interpolate(
      localFrame,
      [cue.atFrame, cue.atFrame + Math.max(1, cue.durationFrames / 2), cue.atFrame + cue.durationFrames],
      [0, 1, 0],
      {easing: Easing.inOut(Easing.ease), extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
    );
  }

  return (
    <div style={{
      border: '2px solid rgba(255,255,255,0.16)',
      background: 'rgba(255,255,255,0.06)',
      borderRadius: 28,
      padding: '34px 38px',
      minHeight: 150,
      transform: `scale(${1 + emphasis * 0.035})`,
      boxShadow: `0 0 ${Math.round(60 * emphasis)}px rgba(94, 234, 212, ${0.35 * emphasis})`,
      whiteSpace: 'pre-wrap',
      overflow: 'hidden'
    }}>
      <div style={{fontSize: 22, opacity: 0.56, marginBottom: 16}}>
        {block.module}
      </div>
      <div style={{fontSize: 38, lineHeight: 1.25, fontWeight: 700}}>
        {blockText(block)}
      </div>
    </div>
  );
};

const SceneView: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const intro = interpolate(frame, [0, 18], [0, 1], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp'
  });

  return (
    <AbsoluteFill style={{
      background: 'linear-gradient(135deg, #07111f 0%, #0b1830 55%, #112347 100%)',
      color: '#f8fafc',
      fontFamily: '"Pretendard", "Noto Sans KR", Arial, sans-serif',
      padding: 96
    }}>
      <div style={{
        opacity: intro,
        transform: `translateY(${(1 - intro) * 18}px)`,
        maxWidth: 1550
      }}>
        <div style={{fontSize: 24, opacity: 0.55, letterSpacing: 1.5, marginBottom: 18}}>
          {String(scene.index + 1).padStart(2, '0')} · {scene.intent}
        </div>
        <div style={{fontSize: 76, fontWeight: 850, lineHeight: 1.05, letterSpacing: -2.2}}>
          {scene.title}
        </div>
        {scene.summary ? (
          <div style={{fontSize: 34, opacity: 0.74, marginTop: 22, maxWidth: 1200}}>
            {scene.summary}
          </div>
        ) : null}
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: scene.blocks.length > 1 ? 'repeat(2, minmax(0, 1fr))' : '1fr',
        gap: 26,
        marginTop: 58,
        alignItems: 'stretch'
      }}>
        {scene.blocks.map((block) => (
          <BlockCard key={block.id} block={block} scene={scene} localFrame={frame} />
        ))}
      </div>

      <div style={{
        position: 'absolute',
        left: 96,
        right: 96,
        bottom: 50,
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: 22,
        opacity: 0.48
      }}>
        <span>{scene.communicationGoal}</span>
        <span>{scene.layout}</span>
      </div>
    </AbsoluteFill>
  );
};

export const DeckVideo: React.FC<{storyboard: Storyboard}> = ({storyboard}) => {
  return (
    <AbsoluteFill>
      {storyboard.scenes.map((scene) => (
        <Sequence
          key={scene.id}
          from={scene.startFrame}
          durationInFrames={scene.durationFrames}
          name={scene.id}
        >
          <SceneView scene={scene} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
