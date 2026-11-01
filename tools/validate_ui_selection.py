"""Independent stdin/stdout adapter. No game path, payload path or execution options."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hf_payload.ui_adapter import new_fixture, validate_selection, response_template
from hf_payload.validator import unique_pairs


def main():
    raw = sys.stdin.buffer.read(16385)
    try:
        if len(raw) > 16384: raise ValueError('request exceeds 16 KiB')
        request = json.loads(raw, object_pairs_hook=unique_pairs,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    except (ValueError, RecursionError) as exc:
        result = response_template()
        result.update(summary='Invalid request: ' + str(exc), conflicts=[{'code':'INVALID_JSON','message':str(exc)}])
        print(json.dumps(result))
        return 2
    # These declarations cover only the newly authored fixture text, never HF/game assets.
    area = new_fixture()
    result = validate_selection(request, area, dict(profile='synthetic', compatibility=True,
                                licensing=True, provenance=True, mapping=True))
    result['fixture_id'] = area.path.name
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'valid' else 2


if __name__ == '__main__': sys.exit(main())
