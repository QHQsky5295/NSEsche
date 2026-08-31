# E1 Homogeneous-20 Low V160 Diagnostic Plan

The homogeneous 20-node low-load comparison remains the sole open paper
section. Frozen baselines, middle/high evidence and all later chapters remain
unchanged.

V159 passed the complete QPR gates but remained at 11/20 throughput wins. Its
effect was localized to E09 and DAG 46: speculative placement reduced completed
DAG-46 requests from 472 to 283 while reducing their mean completed-request
latency from about 338 ms to 60 ms. DAG 46 has a three-edge chain; V159 could
preplace both deeper nonterminal stages, while only the last nonterminal stage
directly precedes the terminal function.

V160 therefore makes one topology-based change: under the unchanged
remaining-work-at-most-5.5 and queue-density-below-8 gates, admit only a
nonterminal function whose immutable children are all terminal. Ready and
terminal players, the SRPT order, the queue-8 scoring router, NSESche welfare,
pricing, common HPA, tapes and references remain unchanged. The rule does not
read the load label, seed, future arrivals or performance outcomes.

The result-blind diagnostic is fixed to E09, E18 and E20 in that order. The
three rows must all be retained. The unchanged 20-seed hybrid gates require
throughput above Orion with at least 12 paired wins (including two of these
three), both QPR conventions above OCS with at least 12 paired wins, and the
frozen three-seed sum gates. The other 17 runs are forbidden unless this
diagnostic passes; a paper claim remains forbidden until a separate complete
training and fresh-confirmation plan passes.
