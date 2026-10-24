import { useEffect } from 'react';
import { axis, installKeyboard } from '../robot/keyboard';
import { useStore } from '../state/store';

const TELEOP_MS = 50;

/**
 * 20 Hz teleop for the real D1 while Manual is on and the bridge is linked (zeros included, so the
 * robot only moves with fresh commands). A timer and not the render loop: a hidden tab is throttled,
 * the server sees stale input and sends zeros.
 */
export function useTeleop() {
  useEffect(() => {
    installKeyboard();
    const id = window.setInterval(() => {
      const s = useStore.getState();
      if (!s.manual || s.mode !== 'single' || !s.realRobot?.connected) return;
      const { fwd, turn, fast } = axis();
      s.send?.({ cmd: 'teleop', fwd, turn, strafe: 0, fast });
    }, TELEOP_MS);
    return () => window.clearInterval(id);
  }, []);
}
