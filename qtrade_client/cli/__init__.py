#!/usr/bin/env python3
import yaml
import os
import os.path
import click
import sys
import logging

from pkg_resources import iter_entry_points
from click_plugins import with_plugins

from ..api import Qtrade

log = logging.getLogger("qtrade-cli")


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


@with_plugins(iter_entry_points('qtrade.plugins'))
@click.group()
@click.option('--context', '-c')
@click.option('--verbose', '-v', default=False, show_default=True)
@click.option('--config-dir', '-d', default="~/.qtctl", show_default=True)
@click.pass_context
def cli(ctx, verbose, config_dir, context):
    root = logging.getLogger()
    level = "DEBUG" if verbose else "INFO"

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    logging.getLogger("qtrade").setLevel(level)

    formatter = logging.Formatter(
        '%(asctime)s [%(name)-15s] [%(levelname)-5s] %(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)

    contexts = {"dev_root":
                Qtrade('http://localhost:9898',
                       key='1:1111111111111111111111111111111111111111111111111111111111111111',
                       origin="builtin")}
    default_context = "dev_root"
    cfg_root = os.path.expanduser(config_dir)
    for filename in os.scandir(cfg_root):
        if filename.name == ".default_context":
            default_context = open(filename.path).read().strip()
        if filename.name.startswith("."):  # Ignore "hidden" files
            continue
        try:
            cfgs = yaml.load(open(filename.path))
            assert isinstance(cfgs, dict)
            for key, cfg in cfgs.items():
                contexts[key] = Qtrade(origin=filename.path, **cfg)
        except Exception as e:
            log.warn("Failed to parse config {}: {}".format(filename, e))
            continue

    # Default to our context if it exists
    active_context = contexts.get(default_context)
    # If they explicity specified a context, use that if it exists
    if context is not None:
        active_context = contexts.get(context)
    else:
        context = default_context

    if active_context is None:
        log.fatal("Failed to set context to {}: only have {}"
                  .format(context, contexts.keys()))
        sys.exit(1)

    print("using profile '{}' from '{}' => {} @ {}"
          .format(bcolors.BOLD + context + bcolors.ENDC,
                  bcolors.BOLD + active_context.origin + bcolors.ENDC,
                  bcolors.OKGREEN + active_context.email + bcolors.ENDC,
                  bcolors.OKBLUE + active_context.endpoint + bcolors.ENDC,
                  ))
    ctx.obj['client'] = active_context


def entry():
    cli(obj={})


if __name__ == "__main__":
    entry()
