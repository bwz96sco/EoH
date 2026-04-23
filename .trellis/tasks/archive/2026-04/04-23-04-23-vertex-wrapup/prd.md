# Finalize Vertex ADC integration and cleanup

## Goal

Clean up the remote Vertex experiment checkout, preserve only the merged Vertex ADC integration in the main branch, tighten experiment workflow rules around launch logs and remote checkout naming, and archive the completed Vertex integration task.

## What I already know

* Vertex ADC support was implemented in `eoh/src/eoh/llm/api_general.py` and `eoh/src/eoh/llm/interface_LLM.py`.
* The main local branch already contains the desired code and workflow changes.
* Remote experiment checkout `/root/code/exp-gcp-vertex-adc` still contains uncommitted LLM adapter changes plus stray `.launch-*` files.
* Remote primary checkout `/root/code/EoH-repro` is dirty for unrelated historical reasons and should not be conflated with this task.

## Requirements

* Remove stray launch logs from the remote Vertex experiment checkout.
* Commit the relevant Vertex ADC cleanup changes in the main local branch.
* Ensure the ABR experiment skill explicitly directs launch logs into canonical experiment directories and not repo-root temp files.
* Archive the completed Vertex ADC Trellis task once cleanup is done.

## Acceptance Criteria

* [ ] Remote `exp-gcp-vertex-adc` no longer contains stray `.launch-*` files.
* [ ] Main local branch has the intended Vertex ADC and workflow updates committed.
* [ ] Experiment workflow skill explicitly discourages repo-root launch logs and clarifies canonical locations.
* [ ] Previous Vertex ADC task is archived.

## Out of Scope

* Cleaning unrelated dirt in `/root/code/EoH-repro`
* Re-running Vertex experiments
