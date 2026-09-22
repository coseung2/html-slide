import React from 'react';
import {AbsoluteFill, interpolate, Sequence, useCurrentFrame} from 'remotion';
import {BlockRenderer} from './renderers';
import type {Block, DesignTokens, Scene, Storyboard} from './types';

const palette = (design: DesignTokens, key: string, fallback: string) =>
  design.palette[key] ?? fallback;

const blocksFor = (scene: Scene, slot: string): Block[] => {
  const ids = new Set(scene.slots[slot] ?? []);
  return scene.blocks.filter((block) => ids.has(block.id));
};

const Slot: React.FC<{
  scene: Scene;
  slot: string;
  frame: number;
  design: DesignTokens;
  grid?: boolean;
}> = ({scene, slot, frame, design, grid = false}) => {
  const blocks = blocksFor(scene, slot);
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: grid
        ? `repeat(${blocks.length >= 5 ? 3 : 2}, minmax(0,1fr))`
        : '1fr',
      gridAutoRows: grid ? '1fr' : undefined,
      gap: 22,
      minWidth: 0,
      minHeight: 0,
      height: '100%'
    }}>
      {blocks.map((block) => (
        <BlockRenderer
          key={block.id}
          block={block}
          scene={scene}
          frame={frame}
          design={design}
        />
      ))}
    </div>
  );
};

const Header: React.FC<{
  scene: Scene;
  design: DesignTokens;
  align?: 'left' | 'center';
}> = ({scene, design, align = 'left'}) => (
  <header style={{textAlign: align, alignSelf: 'start'}}>
    <h1 style={{
      fontSize: scene.layout === 'hero' ? 78 : 64,
      lineHeight: 1.08,
      letterSpacing: -2,
      margin: 0,
      fontWeight: 850,
      color: palette(design, 'ink', '#f7f9fc')
    }}>
      {scene.title}
    </h1>
    {scene.summary ? (
      <p style={{
        margin: align === 'center' ? '24px auto 0' : '24px 0 0',
        maxWidth: 920,
        fontSize: 30,
        lineHeight: 1.38,
        color: palette(design, 'muted', '#b5c0cc')
      }}>
        {scene.summary}
      </p>
    ) : null}
  </header>
);

const SceneView: React.FC<{scene: Scene; design: DesignTokens}> = ({scene, design}) => {
  const frame = useCurrentFrame();
  const transition = scene.transitionFrames > 0
    ? interpolate(frame, [0, scene.transitionFrames], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp'
      })
    : 1;

  const base: React.CSSProperties = {
    width: '100%',
    height: '100%',
    minWidth: 0,
    minHeight: 0
  };

  let content: React.ReactNode;
  switch (scene.layout) {
    case 'comparison':
      content = (
        <div style={{...base, display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: 'auto 1fr', gap: '38px 42px'}}>
          <div style={{gridColumn: '1 / -1'}}><Header scene={scene} design={design} /></div>
          <Slot scene={scene} slot="left" frame={frame} design={design} />
          <div style={{borderLeft: `2px solid ${palette(design, 'line', '#52657a')}`, paddingLeft: 42, minHeight: 0}}>
            <Slot scene={scene} slot="right" frame={frame} design={design} />
          </div>
        </div>
      );
      break;
    case 'split-right':
    case 'image-focus':
      content = (
        <div style={{...base, display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 530px', gap: 70, alignItems: 'stretch'}}>
          <Slot scene={scene} slot="main" frame={frame} design={design} />
          <Header scene={scene} design={design} />
        </div>
      );
      break;
    case 'split-left':
    case 'ranking-board':
    case 'process-flow':
    case 'timeline':
      content = (
        <div style={{
          ...base,
          display: 'grid',
          gridTemplateColumns: scene.layout === 'timeline' ? '600px minmax(0,1fr)' : '530px minmax(0,1fr)',
          gap: scene.layout === 'timeline' ? 60 : 70,
          alignItems: 'stretch'
        }}>
          <Header scene={scene} design={design} />
          <Slot scene={scene} slot="main" frame={frame} design={design} />
        </div>
      );
      break;
    case 'stat-grid':
      content = (
        <div style={{...base, display: 'grid', gridTemplateRows: 'auto 1fr', gap: 38}}>
          <Header scene={scene} design={design} />
          <Slot scene={scene} slot="main" frame={frame} design={design} grid />
        </div>
      );
      break;
    case 'hero':
    case 'quote-focus':
    default:
      content = (
        <div style={{...base, display: 'grid', gridTemplateRows: 'auto 1fr', gap: 44, textAlign: 'center'}}>
          <Header scene={scene} design={design} align="center" />
          <Slot scene={scene} slot="main" frame={frame} design={design} />
        </div>
      );
      break;
  }

  return (
    <AbsoluteFill style={{
      background: palette(design, 'paper', '#08111f'),
      color: palette(design, 'ink', '#f7f9fc'),
      fontFamily: '"HTMLSlide Pretendard", "Pretendard Variable", Pretendard, sans-serif',
      padding: 96,
      boxSizing: 'border-box',
      opacity: transition
    }}>
      {content}
    </AbsoluteFill>
  );
};

export const DeckVideo: React.FC<Storyboard> = (storyboard) => (
  <AbsoluteFill>
    {storyboard.scenes.map((scene) => (
      <Sequence
        key={scene.id}
        from={scene.startFrame}
        durationInFrames={scene.durationFrames}
        name={scene.id}
      >
        <SceneView scene={scene} design={storyboard.design} />
      </Sequence>
    ))}
  </AbsoluteFill>
);
