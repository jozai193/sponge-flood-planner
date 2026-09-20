declare const __SPONGE_MODEL_SOURCE_SHA256__:string;

/** Vite injects a deterministic digest of the executable modelling source tree. */
export const modelSourceSha256=typeof __SPONGE_MODEL_SOURCE_SHA256__==='string'?__SPONGE_MODEL_SOURCE_SHA256__:'development-runtime-unpinned';
