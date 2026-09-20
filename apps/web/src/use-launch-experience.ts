import { useCallback, useEffect, useRef, useState } from "react";

import { readSessionValue, writeSessionValue } from "./api-client";

export function useLaunchExperience() {
  const [launch, setLaunch] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    const forced = params.get("intro") === "1";
    const disabled = params.get("intro") === "0" || params.get("tour") === "1";
    const seen = readSessionValue("sponge-launch-seen") === "1";
    const visible = !disabled && (forced || !seen);
    if (visible) writeSessionValue("sponge-launch-seen", "1");
    return { visible, exiting: false, run: 0 };
  });
  const closeTimer = useRef<number | null>(null);

  const closeLaunch = useCallback(() => {
    if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    setLaunch((previous) => ({ ...previous, exiting: true }));
    closeTimer.current = window.setTimeout(
      () => setLaunch((previous) => ({ ...previous, visible: false, exiting: false })),
      760,
    );
  }, []);

  const playLaunch = useCallback(() => {
    if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    setLaunch((previous) => ({ visible: true, exiting: false, run: previous.run + 1 }));
  }, []);

  useEffect(() => {
    if (!launch.visible) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timer = window.setTimeout(closeLaunch, reduced ? 1800 : 6800);
    return () => window.clearTimeout(timer);
  }, [closeLaunch, launch.run, launch.visible]);

  useEffect(
    () => () => {
      if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    },
    [],
  );

  return { launch, closeLaunch, playLaunch };
}
