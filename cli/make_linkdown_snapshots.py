import argparse
import make_linkdown_snapshots_ops as so


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Duplicate snapshots with single physical-linkdown")
    parser.add_argument(
        "--input_snapshot_base",
        "-i",
        required=True,
        type=str,
        help="Input snapshot base directory",
    )
    parser.add_argument(
        "--output_snapshot_base",
        "-o",
        required=True,
        type=str,
        help="Output snapshot(s) base directory",
    )
    parser.add_argument("--node", "-n", default=None, type=str, help="A node name to draw-off")
    parser.add_argument("--link_regexp", "-l", type=str, help="Link name or pattern regexp to draw-off")
    parser.add_argument("--dry_run", action="store_true", default=False, help="Dry-run")
    args = parser.parse_args()

    so.make_linkdown_snapshots(
        args.input_snapshot_base, args.output_snapshot_base, args.node, args.link_regexp, args.dry_run
    )
