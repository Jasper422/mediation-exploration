"""Generate unestimated single/parallel-mediation structure drafts; stdlib only."""
import argparse
import csv
import itertools
import json
import re
from pathlib import Path


def valid_ids(values, field):
    if not values:
        raise ValueError(f'{field}: at least one ID is required')
    if len(set(values)) != len(values):
        raise ValueError(f'{field}: duplicate IDs are not allowed')
    if any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', v) for v in values):
        raise ValueError(f'{field}: use internal aliases such as M1 or DV1; map original column names separately')
    return list(values)


def generate(mediators, outcomes, exposure='X', singles=None, pairs=None):
    mediators = valid_ids(mediators, 'mediators')
    outcomes = valid_ids(outcomes, 'outcomes')
    valid_ids([exposure], 'exposure')
    if set(mediators) & set(outcomes) or exposure in set(mediators + outcomes):
        raise ValueError('exposure, mediator and outcome aliases must be disjoint')
    singles = mediators[:] if singles is None else list(singles)
    if singles:
        valid_ids(singles, 'single')
    if any(m not in mediators for m in singles):
        raise ValueError('a single-mediator ID is not in mediators')
    requested = list(itertools.combinations(mediators, 2)) if pairs is None else list(pairs)
    canonical = []
    for pair in requested:
        if len(pair) != 2 or pair[0] == pair[1] or any(m not in mediators for m in pair):
            raise ValueError(f'invalid parallel pair: {pair}')
        ordered = tuple(sorted(pair, key=mediators.index))
        if ordered in canonical:
            raise ValueError(f'duplicate parallel pair (order does not define a chain): {pair}')
        canonical.append(ordered)
    structures = [(m,) for m in singles] + canonical
    if not structures:
        raise ValueError('the requested scope contains no candidate models')
    rows = []
    for outcome in outcomes:
        for subset in structures:
            rows.append({
                'model_id': outcome + '__' + '__'.join(subset),
                'exposure': exposure,
                'outcome': outcome,
                'model_type': 'single' if len(subset) == 1 else 'parallel',
                'mediators': '+'.join(subset),
                'specific_paths': len(subset),
                'status': 'draft_unestimated',
                'inclusion_basis': '结构草案；需结合研究背景补充纳入理由，并完成第四步操作者确认',
            })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mediators', nargs='+', required=True, help='internal mediator aliases, e.g. M1 M2 M3')
    parser.add_argument('--outcomes', nargs='+', required=True, help='internal outcome aliases, e.g. DV1 DV2')
    parser.add_argument('--exposure', default='X')
    parser.add_argument('--single', nargs='*', default=None, help='restrict singles; supply this flag alone for none')
    parser.add_argument('--pairs', nargs='*', default=None, help='restrict parallel pairs, e.g. M1+M2 M1+M3; flag alone for none')
    parser.add_argument('--out', type=Path, required=True, help='new draft CSV; existing output is never overwritten')
    args = parser.parse_args()
    pairs = None if args.pairs is None else [tuple(v.split('+')) for v in args.pairs]
    try:
        rows = generate(args.mediators, args.outcomes, args.exposure, args.single, pairs)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open('x', encoding='utf-8-sig', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    except (ValueError, OSError) as error:
        parser.exit(2, f'Error: {error}\n')
    print(json.dumps({
        'output': str(args.out.resolve()),
        'models': len(rows),
        'specific_paths': sum(row['specific_paths'] for row in rows),
        'status': 'draft_unestimated',
        'note': 'No data were read, models fitted, or operator confirmations inferred.',
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
