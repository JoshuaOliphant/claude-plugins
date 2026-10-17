# Benchmarks

Depth for performance claims in `compost:diagnose` step 6 and `compost:verify` step 6. A benchmark
produces a number; this checklist decides whether the number means what you think.

## Write the claim first

Before you run anything, write the claim in one sentence: what is faster or slower, by roughly how
much, on which workload. A claim written after the run bends to fit whatever came out.

## Seven questions

Answer each one in writing, next to the number.

1. **Why not double?** Name the limiter that stops the result from being twice as good: CPU, I/O,
   a lock, the network, a fixed cost. Show it with a profile or a measurement. A guess from reading
   the code is not a limiter.
2. **Is each side tuned?** Both sides get the same care: warm caches or cold on both, the same
   build flags, the same data, the same machine. A tuned new path against a default old one
   measures the tuning.
3. **What are the limits?** Say where the result stops holding: input size, concurrency, hardware,
   data shape. A win at one size can be a loss at another.
4. **Did anything error?** Check the logs and exit codes of every run. Failed requests finish fast,
   so errors often look like a speedup.
5. **Does it reproduce?** Run each side 5 times, alternating A and B so drift hits both. Report the
   median and the range. If the ranges overlap, you have not shown a difference.
6. **Does it matter end to end?** Measure the path the user waits on, not just the piece you
   changed. A 50% win on a step that takes 1% of the request is a 0.5% win.
7. **Did it happen at all?** Prove the code you changed ran during the measurement: a counter, a
   log line, a profile frame. Skipped work, a cache hit, or a stale build all look fast.

## Close with one verdict

End with exactly one of: faster, slower, no measurable difference, or inconclusive. Put the median,
the range, and the answers above beside it. Inconclusive is a valid result; say what would settle
it.
