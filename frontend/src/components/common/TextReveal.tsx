import React, { useMemo } from 'react';
import { motion, type Variants } from 'framer-motion';

/* ─────────────────────────────────────────────────────────
 *  TextReveal  –  Staggered character-by-character entrance
 *
 *  Each character rises from below + fades in when the
 *  container scrolls into the viewport.  Words stay together
 *  so we don't get mid-word line breaks.
 * ────────────────────────────────────────────────────────── */

interface TextRevealProps {
  /** The text to animate. Supports plain strings.  */
  text: string;
  /** HTML tag to render. Default: "span" */
  as?: keyof React.JSX.IntrinsicElements;
  /** Extra className forwarded to the wrapper element */
  className?: string;
  /** Per-character stagger delay in seconds. Default 0.025 */
  stagger?: number;
  /** Vertical rise distance in px. Default 28 */
  yOffset?: number;
  /** Viewport intersection threshold (0-1). Default 0.35 */
  viewportThreshold?: number;
  /** Only animate once? Default true */
  once?: boolean;
  /** Child elements to render after animated text (e.g. inline icons) */
  children?: React.ReactNode;
}

const charVariants: Variants = {
  hidden: (yOffset: number) => ({
    y: yOffset,
    opacity: 0,
    filter: 'blur(4px)',
  }),
  visible: {
    y: 0,
    opacity: 1,
    filter: 'blur(0px)',
    transition: {
      type: 'spring',
      damping: 18,
      stiffness: 120,
      mass: 0.6,
    },
  },
};

export const TextReveal: React.FC<TextRevealProps> = ({
  text,
  as: Tag = 'span',
  className = '',
  stagger = 0.025,
  yOffset = 28,
  viewportThreshold = 0.35,
  once = true,
  children,
}) => {
  /* Split text into words, then into characters, preserving word grouping. */
  const words = useMemo(() => text.split(' '), [text]);

  /* We need a MotionComponent for the wrapper — use motion.create for
     custom tag names so we aren't restricted to motion.div / motion.span. */
  const MotionWrapper = motion[Tag as 'div'] ?? motion.div;

  return (
    <MotionWrapper
      className={className}
      initial="hidden"
      whileInView="visible"
      viewport={{ once, amount: viewportThreshold }}
      transition={{ staggerChildren: stagger }}
      aria-label={text}
      style={{ display: 'inline' }}
    >
      {words.map((word, wIdx) => (
        <span
          key={wIdx}
          style={{ display: 'inline-block', whiteSpace: 'pre' }}
        >
          {word.split('').map((char, cIdx) => (
            <motion.span
              key={`${wIdx}-${cIdx}`}
              variants={charVariants}
              custom={yOffset}
              style={{ display: 'inline-block' }}
              aria-hidden="true"
            >
              {char}
            </motion.span>
          ))}
          {/* Add a space after each word except the last */}
          {wIdx < words.length - 1 && (
            <motion.span
              variants={charVariants}
              custom={yOffset}
              style={{ display: 'inline-block', width: '0.3em' }}
              aria-hidden="true"
            >
              {'\u00A0'}
            </motion.span>
          )}
        </span>
      ))}
      {children}
    </MotionWrapper>
  );
};

/* ─────────────────────────────────────────────────────────
 *  SectionReveal  –  Fade-and-rise wrapper for whole blocks
 *
 *  Wrap any JSX children. The block fades up as a unit when
 *  it enters the viewport — complementary to per-char reveals.
 * ────────────────────────────────────────────────────────── */

interface SectionRevealProps {
  children: React.ReactNode;
  className?: string;
  /** Delay before the animation begins (seconds). Default 0 */
  delay?: number;
  /** Vertical offset in px. Default 40 */
  yOffset?: number;
  /** Only animate once? Default true */
  once?: boolean;
  /** Viewport amount threshold 0-1. Default 0.2 */
  viewportThreshold?: number;
}

export const SectionReveal: React.FC<SectionRevealProps> = ({
  children,
  className = '',
  delay = 0,
  yOffset = 40,
  once = true,
  viewportThreshold = 0.2,
}) => (
  <motion.div
    className={className}
    initial={{ opacity: 0, y: yOffset, filter: 'blur(4px)' }}
    whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
    viewport={{ once, amount: viewportThreshold }}
    transition={{
      duration: 0.65,
      ease: [0.22, 1, 0.36, 1],
      delay,
    }}
  >
    {children}
  </motion.div>
);
