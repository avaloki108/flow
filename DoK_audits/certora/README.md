# Certora scaffold for flow

## Quickstart

1. **Set up secrets**: Put `CERTORAKEY` in `/home/dok/web3/sabier/flow/.env.local`
   ```bash
   echo "CERTORAKEY=your_key_here" > .env.local
   ```

2. **Review generated spec**: Edit `certora/specs/SablierFlow.spec` to match actual contract methods

3. **Run baseline verification**:
   ```bash
   ./scripts/certora_run.sh certora/confs/SablierFlow.conf
   ```

4. **Triage failures** (if any):
   ```bash
   ./scripts/certora_triage.sh certora/out/SablierFlow.log
   ```

## Iteration Workflow

### Focus on specific rule:
```bash
./scripts/certora_run.sh certora/confs/SablierFlow.conf --rule rule_name
```

### Focus on specific method:
```bash
./scripts/certora_run.sh certora/confs/SablierFlow.conf --method method_name
```

## Notes

- Contract/spec names are auto-detected. Adjust `verify` in `certora/confs/SablierFlow.conf` if needed.
- Start with minimal spec (3-8 invariants + 2-5 rules), then expand.
- Check `certora/out/summary.md` after runs for triage recommendations.
- See `CERTORA_SKILL.md` in repo root for repo-specific invariants and patterns.

## Repo-Specific Priorities

- **Debt monotonicity**: totalDebt increases linearly when running
- **Pause correctness**: pause stops debt accrual
- **Withdraw bounds**: withdraw <= coveredDebt
- **Refund correctness**: refund doesn't steal owed amounts