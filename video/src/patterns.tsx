import React from 'react';
import {patternState} from './motion';
import type {Block, DesignTokens, Scene} from './types';

type Props = {
  block: Block;
  scene: Scene;
  frame: number;
  design: DesignTokens;
  children: React.ReactNode;
};

const color = (design: DesignTokens, key: string, fallback: string) =>
  design.palette[key] ?? fallback;

const clamp = (value: number) => Math.max(0, Math.min(1, value));

export const scrambleText = (value: string, progress: number): string => {
  const glyphs = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%?';
  const keep = Math.floor(value.length * clamp(progress));
  return [...value].map((char, index) => {
    if (/\s/u.test(char) || index < keep) return char;
    return glyphs[(index * 7 + value.length * 3) % glyphs.length];
  }).join('');
};

const Shapes: React.FC<{design: DesignTokens; pulse: number}> = ({design, pulse}) => (
  <>
    {[0, 1, 2].map((index) => (
      <span key={index} style={{
        position: 'absolute',
        width: 90 + index * 34,
        height: 90 + index * 34,
        borderRadius: index === 1 ? 18 : '50%',
        background: index === 2 ? color(design, 'ink', '#fff') : color(design, 'accent', '#54a8ff'),
        opacity: 0.08 + pulse * 0.18,
        left: (8 + index * 31) + '%',
        top: (12 + (index % 2) * 54) + '%',
        transform: 'translate(' + ((1 - pulse) * (index % 2 ? 100 : -100)) + 'px,' + ((1 - pulse) * 45) + 'px) rotate(' + (pulse * (index + 1) * 55) + 'deg)'
      }} />
    ))}
  </>
);

const Particles: React.FC<{design: DesignTokens; pulse: number}> = ({design, pulse}) => (
  <>
    {Array.from({length: 18}, (_, index) => {
      const angle = (Math.PI * 2 * index) / 18;
      const radius = 240 * (1 - pulse);
      return (
        <span key={index} style={{
          position: 'absolute',
          width: 9 + (index % 4) * 3,
          height: 9 + (index % 4) * 3,
          borderRadius: '50%',
          background: index % 3 === 0 ? color(design, 'ink', '#fff') : color(design, 'accent', '#54a8ff'),
          left: 'calc(50% + ' + (Math.cos(angle) * radius) + 'px)',
          top: 'calc(50% + ' + (Math.sin(angle) * radius) + 'px)',
          opacity: pulse * 0.72
        }} />
      );
    })}
  </>
);

const Overlay: React.FC<{pattern: string; progress: number; pulse: number; design: DesignTokens}> = ({
  pattern, progress, pulse, design
}) => {
  const accent = color(design, 'accent', '#54a8ff');
  const paper = color(design, 'paper', '#08111f');
  const ink = color(design, 'ink', '#f7f9fc');
  if (pattern === 'flat-shape') return <Shapes design={design} pulse={pulse} />;
  if (pattern === 'particle-warp') return <Particles design={design} pulse={pulse} />;
  if (pattern === 'liquid-morph') {
    return <>
      {[0, 1, 2].map((index) => (
        <span key={index} style={{
          position: 'absolute',
          width: 240 + index * 90,
          height: 170 + index * 70,
          left: (8 + index * 23) + '%',
          top: (12 + (index % 2) * 40) + '%',
          borderRadius: (35 + pulse * 25) + '% ' + (65 - pulse * 20) + '% ' + (45 + pulse * 20) + '% ' + (55 - pulse * 15) + '%',
          background: accent,
          opacity: 0.04 + pulse * 0.08,
          transform: 'rotate(' + (((index - 1) * 12) + pulse * 18) + 'deg) scale(' + (0.85 + pulse * 0.18) + ')'
        }} />
      ))}
    </>;
  }
  if (pattern === 'card-stack-3d' || pattern === 'paper-cut') {
    return <>
      {[3, 2, 1].map((depth) => (
        <span key={depth} style={{
          position: 'absolute',
          inset: 12 + depth * 12,
          borderRadius: pattern === 'paper-cut' ? 8 : 24,
          border: '2px solid ' + accent + '55',
          background: pattern === 'paper-cut' ? ink : paper,
          opacity: 0.05 + pulse * 0.08,
          transform: 'translate(' + (depth * (1 - progress) * -26) + 'px,' + (depth * (1 - progress) * 20) + 'px) rotate(' + (pattern === 'paper-cut' ? (depth - 2) * 2.5 : 0) + 'deg)'
        }} />
      ))}
    </>;
  }
  if (pattern === 'occlusion') {
    return <span style={{
      position: 'absolute', zIndex: 4, top: 0, bottom: 0, width: '34%',
      left: (-38 + progress * 150) + '%', background: accent, opacity: pulse * 0.9,
      transform: 'skewX(-12deg)'
    }} />;
  }
  if (pattern === 'swiss-grid') {
    return <span style={{
      position: 'absolute', inset: 0, opacity: pulse * 0.22,
      backgroundImage: 'linear-gradient(to right,' + accent + ' 1px,transparent 1px),linear-gradient(to bottom,' + accent + ' 1px,transparent 1px)',
      backgroundSize: '12.5% 100%,100% 25%'
    }} />;
  }
  if (pattern === 'street-collage') {
    return <>
      {[-1, 0, 1].map((index) => (
        <span key={index} style={{
          position: 'absolute',
          width: (48 + index * 7) + '%',
          height: 34,
          left: (18 + index * 15) + '%',
          top: (18 + (index + 1) * 25) + '%',
          background: index === 0 ? accent : ink,
          opacity: pulse * 0.16,
          transform: 'rotate(' + (index * 5 - 2) + 'deg) translateX(' + ((1 - progress) * index * 90) + 'px)'
        }} />
      ))}
    </>;
  }
  if (pattern === 'path-drawing') {
    return <svg viewBox="0 0 1000 600" preserveAspectRatio="none" style={{position:'absolute', inset:0, width:'100%', height:'100%', overflow:'visible'}}>
      <rect x="12" y="12" width="976" height="576" rx="34" fill="none" stroke={accent} strokeWidth="8"
        pathLength={1} strokeDasharray={1} strokeDashoffset={1 - progress} opacity={0.2 + pulse * 0.7} />
    </svg>;
  }
  if (pattern === 'ui-motion') {
    return <span style={{
      position:'absolute', right:24, top:24, width:14, height:14, borderRadius:'50%',
      background:accent, boxShadow:'-24px 0 0 ' + accent + '88,-48px 0 0 ' + accent + '44',
      opacity:pulse * 0.9
    }} />;
  }
  return null;
};

export const MotionPattern: React.FC<Props> = ({block, scene, frame, design, children}) => {
  const state = patternState(scene, block.id, frame);
  if (!state) return <>{children}</>;
  const {pattern, progress, pulse} = state;
  let transform = 'none';
  let opacity = 1;
  let filter = 'none';
  let clipPath = 'none';
  let textShadow: string | undefined;
  let fontVariationSettings: string | undefined;

  if (pattern === 'kinetic-type') {
    transform = 'translateY(' + ((1 - progress) * 42) + 'px) scale(' + (0.72 + progress * 0.28 + pulse * 0.06) + ')';
    opacity = 0.12 + progress * 0.88;
  } else if (pattern === 'info-motion') {
    transform = 'translateY(' + ((1 - progress) * 22) + 'px)';
    opacity = 0.25 + progress * 0.75;
  } else if (pattern === 'ui-motion') {
    transform = 'translateX(' + ((1 - progress) * 54) + 'px) scale(' + (0.96 + progress * 0.04) + ')';
    opacity = 0.3 + progress * 0.7;
  } else if (pattern === 'card-stack-3d') {
    transform = 'perspective(1000px) rotateX(' + ((1 - progress) * 18) + 'deg) rotateY(' + ((1 - progress) * -12) + 'deg) translateZ(' + ((1 - progress) * -80) + 'px)';
  } else if (pattern === 'glitch') {
    const jump = Math.sin(frame * 2.4) * pulse * 12;
    transform = 'translateX(' + jump + 'px)';
    filter = 'drop-shadow(' + (pulse * 8) + 'px 0 #ff2d55) drop-shadow(' + (-pulse * 8) + 'px 0 #00d8ff)';
  } else if (pattern === 'isometric-build') {
    transform = 'perspective(1100px) rotateX(' + ((1 - progress) * 52) + 'deg) rotateZ(' + ((1 - progress) * -18) + 'deg) scale(' + (0.84 + progress * 0.16) + ')';
    opacity = 0.25 + progress * 0.75;
  } else if (pattern === 'type-mask') {
    clipPath = 'inset(0 ' + ((1 - progress) * 100) + '% 0 0)';
  } else if (pattern === 'environment-type') {
    transform = 'perspective(1200px) rotateY(' + ((1 - progress) * 28) + 'deg) translateX(' + ((1 - progress) * -65) + 'px)';
    opacity = 0.22 + progress * 0.78;
  } else if (pattern === 'scramble-decode') {
    filter = 'blur(' + ((1 - progress) * 2.4) + 'px) contrast(' + (1 + pulse * 0.45) + ')';
    transform = 'translateX(' + (Math.sin(frame * 1.7) * pulse * 5) + 'px)';
  } else if (pattern === 'variable-font') {
    fontVariationSettings = '"wght" ' + Math.round(280 + progress * 520) + ', "wdth" ' + Math.round(82 + progress * 18);
  } else if (pattern === 'extruded-type') {
    const depth = Math.round((1 - progress + pulse) * 8);
    textShadow = Array.from({length: Math.max(1, depth)}, (_, index) =>
      (index + 1) + 'px ' + (index + 1) + 'px 0 ' + color(design, 'accent', '#54a8ff')
    ).join(',');
    transform = 'translate(' + (-depth / 2) + 'px,' + (-depth / 2) + 'px)';
  } else if (pattern === 'paper-cut' || pattern === 'street-collage') {
    transform = 'rotate(' + ((1 - progress) * -2.5) + 'deg) scale(' + (0.96 + progress * 0.04) + ')';
    opacity = 0.35 + progress * 0.65;
  }

  return <div style={{position:'relative', width:'100%', height:'100%', minWidth:0, minHeight:0}}>
    <div style={{
      position:'relative', zIndex:2, width:'100%', height:'100%', transform,
      transformOrigin:'50% 50%', opacity, filter, clipPath, textShadow, fontVariationSettings
    }}>
      {children}
    </div>
    <div aria-hidden style={{position:'absolute', inset:0, zIndex:3, pointerEvents:'none', overflow:'hidden'}}>
      <Overlay pattern={pattern} progress={progress} pulse={pulse} design={design} />
    </div>
  </div>;
};
