import React from 'react';
import {interpolate} from 'remotion';
import {cueCompletion, cuePulse, hasCue, sequenceItemProgress} from './motion';
import type {Block, DesignTokens, Scene} from './types';

type RendererProps = {
  block: Block;
  scene: Scene;
  frame: number;
  design: DesignTokens;
};

const palette = (design: DesignTokens, key: string, fallback: string) =>
  design.palette[key] ?? fallback;

const viz = (design: DesignTokens, key: string, fallback: string) =>
  design.dataviz[key] ?? fallback;

const number = (value: unknown, fallback = 0): number =>
  typeof value === 'number' && Number.isFinite(value) ? value : fallback;

const string = (value: unknown, fallback = ''): string =>
  typeof value === 'string' ? value : fallback;

const formatNumber = (value: number): string =>
  new Intl.NumberFormat('en-US', {maximumFractionDigits: 4}).format(value);

const Frame: React.FC<RendererProps & {children: React.ReactNode; transparent?: boolean}> = ({
  block,
  scene,
  frame,
  design,
  children,
  transparent = false
}) => {
  const focus = cuePulse(scene, block.id, 'focus', frame);
  return (
    <div style={{
      width: '100%',
      height: '100%',
      minHeight: 0,
      boxSizing: 'border-box',
      borderRadius: 28,
      border: transparent ? 'none' : `2px solid ${palette(design, 'line', '#52657a')}55`,
      background: transparent ? 'transparent' : palette(design, 'surface', '#122033'),
      padding: transparent ? 0 : 32,
      transform: `scale(${1 + focus * 0.035})`,
      boxShadow: focus > 0
        ? `0 0 ${Math.round(72 * focus)}px ${palette(design, 'accent', '#54a8ff')}66`
        : 'none',
      overflow: 'hidden'
    }}>
      {children}
    </div>
  );
};

const Metric: React.FC<RendererProps> = (props) => {
  const {block, scene, frame, design} = props;
  const value = number(block.data.value);
  const count = hasCue(scene, block.id, 'number-count')
    ? cueCompletion(scene, block.id, 'number-count', frame)
    : 1;
  const shown = value * count;
  return (
    <Frame {...props}>
      <div style={{fontSize: 28, color: palette(design, 'muted', '#b5c0cc'), marginBottom: 18}}>
        {string(block.data.label)}
      </div>
      <div style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: 14,
        color: palette(design, 'ink', '#f7f9fc')
      }}>
        <strong style={{fontSize: 92, lineHeight: 1, letterSpacing: -3}}>
          {formatNumber(shown)}
        </strong>
        {string(block.data.unit) ? (
          <span style={{fontSize: 32, color: palette(design, 'accent', '#54a8ff')}}>
            {string(block.data.unit)}
          </span>
        ) : null}
      </div>
      {string(block.data.detail) ? (
        <div style={{fontSize: 25, marginTop: 22, color: palette(design, 'muted', '#b5c0cc')}}>
          {string(block.data.detail)}
        </div>
      ) : null}
    </Frame>
  );
};

const Ranking: React.FC<RendererProps> = (props) => {
  const {block, scene, frame, design} = props;
  const items = Array.isArray(block.data.items) ? block.data.items : [];
  return (
    <Frame {...props} transparent>
      <div style={{display: 'grid', gap: 12}}>
        {items.map((raw, index) => {
          const item = raw as Record<string, unknown>;
          const progress = sequenceItemProgress(scene, block.id, index, frame);
          return (
            <div key={index} style={{
              display: 'grid',
              gridTemplateColumns: '72px minmax(0,1fr) 180px',
              alignItems: 'center',
              minHeight: 76,
              padding: '0 24px',
              borderRadius: 18,
              background: index === 0
                ? palette(design, 'accent', '#54a8ff')
                : palette(design, 'surface', '#122033'),
              color: index === 0 ? palette(design, 'paper', '#08111f') : palette(design, 'ink', '#f7f9fc'),
              opacity: 0.22 + progress * 0.78,
              transform: `translateX(${(1 - progress) * 22}px)`
            }}>
              <strong style={{fontSize: 28}}>{String(index + 1).padStart(2, '0')}</strong>
              <span style={{fontSize: 30, fontWeight: 720}}>{string(item.label)}</span>
              <strong style={{fontSize: 34, textAlign: 'right'}}>{formatNumber(number(item.value))}</strong>
            </div>
          );
        })}
      </div>
    </Frame>
  );
};

const SequenceList: React.FC<RendererProps & {mode: 'timeline' | 'list' | 'process'}> = (props) => {
  const {block, scene, frame, design, mode} = props;
  const items = Array.isArray(block.data.items) ? block.data.items : [];
  const horizontal = mode === 'process';
  return (
    <Frame {...props} transparent>
      <div style={{
        display: 'grid',
        gridTemplateColumns: horizontal ? `repeat(${items.length}, minmax(0,1fr))` : '1fr',
        gap: horizontal ? 16 : 18,
        height: '100%',
        alignItems: 'stretch'
      }}>
        {items.map((raw, index) => {
          const progress = sequenceItemProgress(scene, block.id, index, frame);
          return (
            <div key={index} style={{
              display: 'grid',
              gridTemplateColumns: horizontal ? '1fr' : '70px minmax(0,1fr)',
              alignItems: 'center',
              gap: 18,
              padding: horizontal ? '24px 18px' : '16px 22px',
              borderRadius: 20,
              background: palette(design, 'surface', '#122033'),
              border: `2px solid ${palette(design, 'line', '#52657a')}55`,
              opacity: 0.2 + progress * 0.8,
              transform: `translateY(${(1 - progress) * 18}px)`,
              textAlign: horizontal ? 'center' : 'left'
            }}>
              <strong style={{
                fontSize: horizontal ? 34 : 26,
                color: palette(design, 'accent', '#54a8ff')
              }}>
                {String(index + 1).padStart(2, '0')}
              </strong>
              <span style={{fontSize: horizontal ? 27 : 30, lineHeight: 1.28, fontWeight: 650}}>
                {string(raw)}
              </span>
            </div>
          );
        })}
      </div>
    </Frame>
  );
};

const BarChart: React.FC<RendererProps> = (props) => {
  const {block, scene, frame, design} = props;
  const items = Array.isArray(block.data.items) ? block.data.items : [];
  const values = items.map((raw) => number((raw as Record<string, unknown>).value));
  const max = Math.max(1, ...values);
  const grow = hasCue(scene, block.id, 'chart-grow')
    ? cueCompletion(scene, block.id, 'chart-grow', frame)
    : 1;
  return (
    <Frame {...props}>
      <div style={{fontSize: 25, color: palette(design, 'muted', '#b5c0cc'), marginBottom: 20}}>
        {string(block.data.label)}
      </div>
      <div style={{display: 'grid', gap: 18}}>
        {items.map((raw, index) => {
          const item = raw as Record<string, unknown>;
          const value = number(item.value);
          return (
            <div key={index} style={{
              display: 'grid',
              gridTemplateColumns: '180px minmax(0,1fr) 120px',
              alignItems: 'center',
              gap: 18
            }}>
              <span style={{fontSize: 25}}>{string(item.label)}</span>
              <div style={{
                height: 28,
                borderRadius: 999,
                background: palette(design, 'line', '#52657a') + '33',
                overflow: 'hidden'
              }}>
                <div style={{
                  height: '100%',
                  width: `${(value / max) * grow * 100}%`,
                  borderRadius: 999,
                  background: viz(design, `viz-${(index % 6) + 1}`, palette(design, 'accent', '#54a8ff'))
                }} />
              </div>
              <strong style={{fontSize: 27, textAlign: 'right'}}>{formatNumber(value)}</strong>
            </div>
          );
        })}
      </div>
    </Frame>
  );
};

const LineChart: React.FC<RendererProps> = (props) => {
  const {block, scene, frame, design} = props;
  const items = Array.isArray(block.data.items) ? block.data.items : [];
  const values = items.map((raw) => number((raw as Record<string, unknown>).value));
  const low = Math.min(0, ...values);
  const high = Math.max(0, ...values);
  const span = high - low || 1;
  const points = items.map((raw, index) => {
    const value = number((raw as Record<string, unknown>).value);
    const x = 90 + index * (820 / Math.max(1, items.length - 1));
    const y = 330 - ((value - low) / span) * 250;
    return {x, y, value, label: string((raw as Record<string, unknown>).label)};
  });
  const grow = hasCue(scene, block.id, 'chart-grow')
    ? cueCompletion(scene, block.id, 'chart-grow', frame)
    : 1;
  return (
    <Frame {...props}>
      <div style={{fontSize: 25, color: palette(design, 'muted', '#b5c0cc'), marginBottom: 8}}>
        {string(block.data.label)}
      </div>
      <svg viewBox="0 0 1000 410" style={{width: '100%', height: 'calc(100% - 38px)'}}>
        <line
          x1="55"
          x2="950"
          y1={330 - ((0 - low) / span) * 250}
          y2={330 - ((0 - low) / span) * 250}
          stroke={palette(design, 'line', '#52657a')}
          strokeWidth="2"
          opacity="0.55"
        />
        <polyline
          points={points.map((point) => `${point.x},${point.y}`).join(' ')}
          fill="none"
          stroke={viz(design, 'viz-1', palette(design, 'accent', '#54a8ff'))}
          strokeWidth="10"
          strokeLinecap="round"
          strokeLinejoin="round"
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - grow}
        />
        {points.map((point, index) => (
          <g key={index} opacity={interpolate(grow, [0.55, 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}>
            <circle cx={point.x} cy={point.y} r="10" fill={viz(design, 'viz-1', palette(design, 'accent', '#54a8ff'))} />
            <text x={point.x} y={point.y - 24} textAnchor="middle" fill={palette(design, 'ink', '#f7f9fc')} fontSize="24" fontWeight="700">
              {formatNumber(point.value)}
            </text>
            <text x={point.x} y="390" textAnchor="middle" fill={palette(design, 'muted', '#b5c0cc')} fontSize="22">
              {point.label}
            </text>
          </g>
        ))}
      </svg>
    </Frame>
  );
};

const ImageBlock: React.FC<RendererProps> = (props) => {
  const {block} = props;
  const src = string(block.data.src);
  const fit = block.module === 'logo' ? 'contain' : string(block.data.fit, 'cover');
  return (
    <Frame {...props} transparent>
      <img
        src={src}
        alt={string(block.data.alt)}
        style={{width: '100%', height: '100%', objectFit: fit as 'contain' | 'cover', borderRadius: 24}}
      />
    </Frame>
  );
};

const Score: React.FC<RendererProps> = (props) => {
  const {block, scene, frame, design} = props;
  const reveal = hasCue(scene, block.id, 'score-reveal')
    ? cueCompletion(scene, block.id, 'score-reveal', frame)
    : 1;
  return (
    <Frame {...props}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr auto 1fr',
        alignItems: 'center',
        gap: 28,
        height: '100%'
      }}>
        <div style={{fontSize: 34, textAlign: 'right', fontWeight: 700}}>{string(block.data.home)}</div>
        <div style={{
          fontSize: 92,
          fontWeight: 850,
          letterSpacing: 6,
          color: palette(design, 'accent', '#54a8ff'),
          transform: `scale(${0.72 + reveal * 0.28})`,
          opacity: reveal
        }}>
          {Math.round(number(block.data.homeScore) * reveal)} : {Math.round(number(block.data.awayScore) * reveal)}
        </div>
        <div style={{fontSize: 34, fontWeight: 700}}>{string(block.data.away)}</div>
      </div>
      {string(block.data.detail) ? (
        <div style={{fontSize: 24, color: palette(design, 'muted', '#b5c0cc'), textAlign: 'center', marginTop: 16}}>
          {string(block.data.detail)}
        </div>
      ) : null}
    </Frame>
  );
};

const Textual: React.FC<RendererProps> = (props) => {
  const {block, design} = props;
  if (block.module === 'quote') {
    return (
      <Frame {...props} transparent>
        <blockquote style={{margin: 0, fontSize: 52, lineHeight: 1.28, fontWeight: 700}}>
          “{string(block.data.text)}”
        </blockquote>
        <div style={{fontSize: 27, marginTop: 28, color: palette(design, 'muted', '#b5c0cc')}}>
          — {string(block.data.author)}
        </div>
      </Frame>
    );
  }
  if (block.module === 'comparison-text') {
    return (
      <Frame {...props}>
        <div style={{fontSize: 25, color: palette(design, 'accent', '#54a8ff'), marginBottom: 18, fontWeight: 750}}>
          {string(block.data.label)}
        </div>
        <div style={{fontSize: 38, lineHeight: 1.32, fontWeight: 680}}>
          {string(block.data.text)}
        </div>
      </Frame>
    );
  }
  return (
    <Frame {...props} transparent>
      <div style={{fontSize: 54, lineHeight: 1.22, fontWeight: 760, letterSpacing: -1.4}}>
        {string(block.data.text)}
      </div>
    </Frame>
  );
};

const Fallback: React.FC<RendererProps> = (props) => (
  <Frame {...props}>
    <div style={{fontSize: 28, lineHeight: 1.35}}>
      {JSON.stringify(props.block.data)}
    </div>
  </Frame>
);

export const BlockRenderer: React.FC<RendererProps> = (props) => {
  switch (props.block.module) {
    case 'metric': return <Metric {...props} />;
    case 'ranking': return <Ranking {...props} />;
    case 'timeline': return <SequenceList {...props} mode="timeline" />;
    case 'bullet-list': return <SequenceList {...props} mode="list" />;
    case 'process': return <SequenceList {...props} mode="process" />;
    case 'bar-chart': return <BarChart {...props} />;
    case 'line-chart': return <LineChart {...props} />;
    case 'image':
    case 'logo': return <ImageBlock {...props} />;
    case 'score': return <Score {...props} />;
    case 'statement':
    case 'quote':
    case 'comparison-text': return <Textual {...props} />;
    default: return <Fallback {...props} />;
  }
};
