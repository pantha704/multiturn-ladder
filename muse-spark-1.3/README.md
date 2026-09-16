# muse-spark-1.3

**Status: BLOCKED — upstream HTTP 500.**

Provider `opencode-go` · model id `muse-spark-1.3-contributor`.

## What was measured

```
muse-spark-1.3-contributor   HTTP 500  "Upstream request failed: [server_error]"   x5 attempts
muse-spark-1.2-contributor   OK        MS12_OK
deepseek-v4.1-flash          OK        DS_OK   (control, same profile, same moment)
```

The control rules out our rig, our credentials, the profile, and the network: **the 500 is
specific to `muse-spark-1.3-contributor` and is upstream of anything we control.** It fails
identically across all reasoning levels, so it is not a reasoning-effort rejection either.

`muse-spark-1.2-contributor` is reachable and available as a substitute.

## Notes

- `-m <model>` overrides are refused in non-interactive mode by a hermes guard
  (*"Refusing this startup model override in non-interactive mode"*) — the model must be pinned in
  the profile's `config.yaml` instead.
- Available opencode-go models at time of writing: 38, including `grok-4.6`, `grok-4.5`,
  `deepseek-v4.1-flash`, `deepseek-v4-pro`, `glm-5.3`, `kimi-k3`, `minimax-m3`, `qwen3.8-max`,
  `gpt-5.6-luna`, `muse-spark-1.3-contributor`, `muse-spark-1.2-contributor`.

## Files

```
evidence/    reserved for transcripts once the model is reachable
```
