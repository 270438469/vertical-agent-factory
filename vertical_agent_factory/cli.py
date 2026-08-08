import argparse
import json
import sys

from .errors import ApprovalRequired, AgentFactoryError
from .evals import run_evals
from .loader import load_domain_package
from .runtime import AgentRuntime
from .validation import validate_package


def _input_values(values):
    result = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError("Input must use key=value: {}".format(value))
        key, raw = value.split("=", 1)
        if raw.lower() in ("true", "false"):
            result[key] = raw.lower() == "true"
        else:
            result[key] = raw
    return result


def build_parser():
    parser = argparse.ArgumentParser(prog="vertical-agent")
    parser.add_argument("--root", default=".", help="Project root")
    subparsers = parser.add_subparsers(dest="command")

    validate = subparsers.add_parser("validate")
    validate.add_argument("--domain", required=True)

    run = subparsers.add_parser("run")
    run.add_argument("--domain", required=True)
    run.add_argument("--task", required=True)
    run.add_argument("--input", action="append", default=[])
    run.add_argument("--approve", action="append", default=[])

    evaluate = subparsers.add_parser("eval")
    evaluate.add_argument("--domain", required=True)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.command:
        build_parser().print_help()
        return 2
    try:
        if args.command == "validate":
            report = validate_package(load_domain_package(args.root, args.domain))
            print(report.format())
            return 0 if report.passed else 1
        if args.command == "run":
            approvals = {capability: True for capability in args.approve}
            runtime = AgentRuntime(args.root, args.domain, approvals=approvals)
            result = runtime.run(args.task, _input_values(args.input))
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        if args.command == "eval":
            results = run_evals(args.root, args.domain)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0 if all(item["passed"] for item in results) else 1
    except ApprovalRequired as exc:
        print(json.dumps({"status": "APPROVAL_REQUIRED", "capability": exc.capability}))
        return 3
    except (AgentFactoryError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}))
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
