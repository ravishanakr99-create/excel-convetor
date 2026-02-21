import { useEffect, useRef, useCallback } from 'react';

interface Particle {
  x: number;
  y: number;
  opacity: number;
  size: number;
}

interface SnakeSegment {
  x: number;
  y: number;
}

interface Snake {
  segments: SnakeSegment[];
  direction: { x: number; y: number };
  targetDirection: { x: number; y: number };
  color: string;
  glowColor: string;
  speed: number;
}

export default function SnakeAnimation({ isActive }: { isActive: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const snakesRef = useRef<Snake[]>([]);
  const foodsRef = useRef<{ x: number; y: number }[]>([]);
  const particlesRef = useRef<Particle[]>([]);
  const lastMoveTimeRef = useRef(0);
  const fadeOpacityRef = useRef(0);
  const mousePosRef = useRef<{ x: number; y: number } | null>(null);
  const clickEffectRef = useRef<{ x: number; y: number; time: number } | null>(null);

  const initSnakes = useCallback((width: number, height: number) => {
    const padding = 100;
    const bottomArea = height - 40; // Keep snakes near bottom where card gap is
    snakesRef.current = [
      {
        segments: [
          { x: padding, y: bottomArea },
          { x: padding - 4, y: bottomArea },
          { x: padding - 8, y: bottomArea },
        ],
        direction: { x: 1, y: -0.2 },
        targetDirection: { x: 1, y: -0.2 },
        color: '#f472b6',
        glowColor: 'rgba(244, 114, 182, 0.6)',
        speed: 2.5,
      },
      {
        segments: [
          { x: width - padding, y: bottomArea - 30 },
          { x: width - padding + 4, y: bottomArea - 30 },
          { x: width - padding + 8, y: bottomArea - 30 },
        ],
        direction: { x: -1, y: 0.2 },
        targetDirection: { x: -1, y: 0.2 },
        color: 'var(--accent-2)',
        glowColor: 'rgba(0, 212, 180, 0.6)',
        speed: 2,
      },
      {
        segments: [
          { x: width / 2, y: bottomArea - 60 },
          { x: width / 2 - 4, y: bottomArea - 60 },
          { x: width / 2 - 8, y: bottomArea - 60 },
        ],
        direction: { x: 0.3, y: -0.5 },
        targetDirection: { x: 0.3, y: -0.5 },
        color: '#a78bfa',
        glowColor: 'rgba(167, 139, 250, 0.6)',
        speed: 3,
      },
    ];
    foodsRef.current = [];
    particlesRef.current = [];
  }, []);

  const spawnFood = useCallback((width: number, height: number) => {
    const padding = 60;
    if (foodsRef.current.length < 3) {
      foodsRef.current.push({
        x: padding + Math.random() * (width - padding * 2),
        y: padding + Math.random() * (height - padding * 2),
      });
    }
  }, []);

  const createParticles = useCallback((x: number, y: number) => {
    for (let i = 0; i < 5; i++) {
      particlesRef.current.push({
        x: x + (Math.random() - 0.5) * 12,
        y: y + (Math.random() - 0.5) * 12,
        opacity: 0.7,
        size: 1.5 + Math.random() * 2.5,
      });
    }
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resizeCanvas = () => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (rect) {
        canvas.width = rect.width;
        canvas.height = rect.height;
        initSnakes(rect.width, rect.height);
      }
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Handle mouse/touch move to attract snakes
    const handleMove = (e: MouseEvent | TouchEvent) => {
      const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
      const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;
      mousePosRef.current = { x: clientX, y: clientY };
    };

    window.addEventListener('mousemove', handleMove);
    window.addEventListener('touchmove', handleMove);

    const animate = (timestamp: number) => {
      if (!ctx || !canvas) return;

      const width = canvas.width;
      const height = canvas.height;

      // Handle fade in/out
      const targetOpacity = isActive ? 1 : 0;
      fadeOpacityRef.current += (targetOpacity - fadeOpacityRef.current) * 0.06;

      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      if (fadeOpacityRef.current < 0.01) {
        animationRef.current = requestAnimationFrame(animate);
        return;
      }

      ctx.globalAlpha = fadeOpacityRef.current * 0.5;

      // Spawn food randomly
      if (Math.random() < 0.02) {
        spawnFood(width, height);
      }

      // Move snakes every 60ms
      if (timestamp - lastMoveTimeRef.current > 60) {
        lastMoveTimeRef.current = timestamp;

        snakesRef.current.forEach((snake, snakeIndex) => {
          // Smooth direction change
          snake.direction.x += (snake.targetDirection.x - snake.direction.x) * 0.2;
          snake.direction.y += (snake.targetDirection.y - snake.direction.y) * 0.2;

          const head = snake.segments[0];

          // Snakes follow cursor when it's near
          if (mousePosRef.current) {
            const cursorDist = Math.sqrt(
              (head.x - mousePosRef.current.x) ** 2 +
              (head.y - mousePosRef.current.y) ** 2
            );
            if (cursorDist < 250) { // Follow radius
              const followX = mousePosRef.current.x - head.x;
              const followY = mousePosRef.current.y - head.y;
              const followMag = Math.sqrt(followX ** 2 + followY ** 2);
              if (followMag > 0) {
                // Strong follow toward cursor
                const followStrength = 0.7;
                snake.targetDirection = {
                  x: (followX / followMag) * followStrength,
                  y: (followY / followMag) * followStrength,
                };
              }
            }
          }

          // Find nearest food
          let nearestFood: { x: number; y: number; index: number } | null = null;
          let minDist = Infinity;
          foodsRef.current.forEach((food, foodIndex) => {
            const dx = food.x - head.x;
            const dy = food.y - head.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < minDist) {
              minDist = dist;
              nearestFood = { ...food, index: foodIndex };
            }
          });

          // Teal snake (index 1) moves more randomly and only sometimes eats food
          const isTealSnake = snakeIndex === 1;

          // Move toward food occasionally (teal snake does this less often)
          const foodSeekChance = isTealSnake ? 0.015 : 0.05;
          if (nearestFood && Math.random() < foodSeekChance) {
            const food = nearestFood as { x: number; y: number };
            const dx = food.x - head.x;
            const dy = food.y - head.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist > 0) {
              snake.targetDirection = {
                x: (dx / dist) * 0.6 + (Math.random() - 0.5) * 0.4,
                y: (dy / dist) * 0.6 + (Math.random() - 0.5) * 0.4,
              };
            }
          }

          // Random wandering (teal snake wanders more)
          const wanderChance = isTealSnake ? 0.08 : 0.03;
          if (Math.random() < wanderChance) {
            const angle = Math.random() * Math.PI * 2;
            const randomness = isTealSnake ? 1.0 : 0.8;
            snake.targetDirection = {
              x: Math.cos(angle) * randomness,
              y: Math.sin(angle) * randomness,
            };
          }

          // Keep within bounds
          const boundPadding = 40;
          if (head.x < boundPadding) snake.targetDirection.x = Math.abs(snake.targetDirection.x);
          if (head.x > width - boundPadding) snake.targetDirection.x = -Math.abs(snake.targetDirection.x);
          if (head.y < boundPadding) snake.targetDirection.y = Math.abs(snake.targetDirection.y);
          if (head.y > height - boundPadding) snake.targetDirection.y = -Math.abs(snake.targetDirection.y);

          // Normalize direction
          const dirMag = Math.sqrt(
            snake.direction.x ** 2 + snake.direction.y ** 2
          );
          if (dirMag > 0) {
            snake.direction.x /= dirMag;
            snake.direction.y /= dirMag;
          }

          const newHead = {
            x: head.x + snake.direction.x * snake.speed,
            y: head.y + snake.direction.y * snake.speed,
          };

          snake.segments.unshift(newHead);

          // Check food collision (teal snake only eats sometimes)
          let ateFood = false;
          const eatChance = isTealSnake ? 0.3 : 1.0;
          foodsRef.current = foodsRef.current.filter((food, foodIndex) => {
            const foodDist = Math.sqrt(
              (newHead.x - food.x) ** 2 + (newHead.y - food.y) ** 2
            );
            if (foodDist < 10 && !ateFood && Math.random() < eatChance) {
              createParticles(food.x, food.y);
              ateFood = true;
              return false;
            }
            return true;
          });

          if (!ateFood) {
            snake.segments.pop();
          }

          // Limit snake length
          if (snake.segments.length > 10) {
            snake.segments = snake.segments.slice(0, 10);
          }
        });
      }

      // Draw food - minimal elegant dots
      foodsRef.current.forEach((food) => {
        // Small subtle glow
        const gradient = ctx.createRadialGradient(
          food.x, food.y, 0,
          food.x, food.y, 6
        );
        gradient.addColorStop(0, 'rgba(255, 255, 255, 0.3)');
        gradient.addColorStop(1, 'transparent');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(food.x, food.y, 6, 0, Math.PI * 2);
        ctx.fill();

        // Tiny food dot
        ctx.beginPath();
        ctx.arc(food.x, food.y, 2, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.fill();
      });

      // Draw snakes
      snakesRef.current.forEach((snake) => {
        if (snake.segments.length > 1) {
          // Snake body
          ctx.strokeStyle = snake.color;
          ctx.lineWidth = 3;
          ctx.lineCap = 'round';
          ctx.lineJoin = 'round';

          ctx.beginPath();
          ctx.moveTo(snake.segments[0].x, snake.segments[0].y);

          for (let i = 1; i < snake.segments.length; i++) {
            const point = snake.segments[i];
            ctx.lineTo(point.x, point.y);
          }

          ctx.stroke();

          // Snake head glow - bigger for visibility
          const head = snake.segments[0];
          const headGradient = ctx.createRadialGradient(
            head.x, head.y, 0,
            head.x, head.y, 25
          );
          headGradient.addColorStop(0, snake.glowColor);
          headGradient.addColorStop(1, 'transparent');
          ctx.fillStyle = headGradient;
          ctx.beginPath();
          ctx.arc(head.x, head.y, 25, 0, Math.PI * 2);
          ctx.fill();
          
          // Snake head - bigger for visibility
          ctx.beginPath();
          ctx.arc(head.x, head.y, 7, 0, Math.PI * 2);
          ctx.fillStyle = snake.color;
          ctx.fill();
        }
      });

      // Update and draw particles
      particlesRef.current = particlesRef.current.filter((p) => {
        p.opacity -= 0.02;
        p.y -= 0.4;
        p.x += (Math.random() - 0.5) * 0.6;

        if (p.opacity > 0) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(255, 255, 255, ${p.opacity})`;
          ctx.fill();
          return true;
        }
        return false;
      });

      ctx.globalAlpha = 1;
      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('touchmove', handleMove);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isActive, initSnakes, spawnFood, createParticles]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 0,
      }}
    />
  );
}
