import { useCallback, useEffect, useRef, useState } from "react";

export function useLaunchExperience() {
  const [launch, setLaunch] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    const forced = params.get("intro") === "1";
    const directApp = params.has("bundle") || params.get("tour") === "1";
    const disabled = params.get("intro") === "0";
    const visible = !disabled && (forced || !directApp);
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
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeLaunch();
    };
    window.addEventListener("keydown", keydown);
    return () => window.removeEventListener("keydown", keydown);
  }, [closeLaunch, launch.visible]);

  useEffect(
    () => () => {
      if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    },
    [],
  );

  return { launch, closeLaunch, playLaunch };
}
