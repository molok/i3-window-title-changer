#!/usr/bin/env python3
"""
i3 window title changer is a small daemon for i3wm which connects to it via unix socket,
listens for new window and title change events and change them to something simple
based on the user defined patterns in the rules file.
"""
import configparser
import os
import pprint
import re
import subprocess
import sys

import i3ipc

DEFAULT_RULE_PATH = '~/.config/i3/window-title-changer-rules'
title_rules = []


def to_regex(regex):
    if regex:
        return re.compile(regex)
    else:
        return None


def parse_rule(rule, rule_name):
    r = {'name': rule_name,
         'class': rule.get('class', None),
         'class_regex': rule.get('class_regex', None),
         'title': rule.get('title', None),
         'title_regex': to_regex(rule.get('title_regex', None)),
         'new_title': rule.get('new_title', None)}

    if r.get('title') and r.get('title_regex'):
        raise Exception('only one of "title" and "title_regex" accepted')

    if not r['class'] and not r['title_regex'] and not r['title']:
        raise Exception(
            'Either a class, title_regex or title required, but was missing for rule {}'.format(rule_name))

    if r.get('new_title') is None:
        raise Exception('a new_title is required'.format(rule_name))

    return r


def read_rules_file(rules_file):
    print('Reading rules file:', rules_file)
    global title_rules
    rules_file = os.path.expanduser(rules_file)
    config = configparser.ConfigParser()
    config.read(rules_file)
    rules = []
    for rule_name in config.sections():
        rules.append(parse_rule(config[rule_name], rule_name))
    title_rules = rules
    pprint.pprint(title_rules)


def handle_title_change(i3, event):
    window_id = event.container.id
    current_title = event.container.name
    window_class = event.container.window_class
    print('"{}" class={}, id={}'.format(current_title, window_class, window_id))

    new_title = None

    for rule in title_rules:
        if rule['class']:
            if rule['class'] in window_class:
                new_title = rule['new_title']
            else:
                new_title = None
                continue

        if rule['class_regex']:
            if re.search(rule['class_regex'], window_class):
                new_title = rule['new_title']
            else:
                new_title = None
                continue

        if rule['title']:
            if rule['title'] in current_title:
                new_title = rule['new_title']
                break
            else:
                new_title = None
                continue

        if rule['title_regex']:
            if re.search(rule['title_regex'], current_title):
                new_title = re.sub(rule['title_regex'], rule['new_title'], current_title)
                break
            else:
                new_title = None
                continue

    if new_title:
        print("new_title: {}".format(new_title))
        window_i3 = i3.get_tree().find_by_id(window_id)
        if window_i3:
            window_i3.command('title_format ' + new_title)


def on_new_window(i3, event):
    print('New window ', end=' ')
    handle_title_change(i3, event)


def on_title_change(i3, event):
    print('Window title changed ', end=' ')
    handle_title_change(i3, event)


def parse_cli_arguments():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rules-file', dest='rules_file', default=DEFAULT_RULE_PATH,
                        help='File containing rule definitions (default: ' + DEFAULT_RULE_PATH + ')')
    return parser.parse_args()


def print_i3_socket_path():
    print('$I3SOCK:', os.environ.get('I3SOCK'))
    print('i3 --get-socket-path:', end=' ', flush=True)
    subprocess.run(['i3', '--get-socketpath'])


def main(rules_file):
    print_i3_socket_path()
    read_rules_file(rules_file)

    i3 = i3ipc.Connection()
    i3.on("window::new", on_new_window)
    i3.on("window::title", on_title_change)
    # Run main loop and wait for events
    i3.main()


if __name__ == '__main__':
    args = parse_cli_arguments()
    exitcode = main(args.rules_file)
    sys.exit(exitcode)
