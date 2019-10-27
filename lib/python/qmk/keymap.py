"""Functions that help you work with QMK keymaps.
"""
import os
from traceback import format_exc
import re
import glob

import qmk.path
import qmk.makefile
from qmk.errors import NoSuchKeyboardError

# The `keymap.c` template to use when a keyboard doesn't have its own
DEFAULT_KEYMAP_C = """#include QMK_KEYBOARD_H

/* THIS FILE WAS GENERATED!
 *
 * This file was generated by qmk-compile-json. You may or may not want to
 * edit it directly.
 */

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
__KEYMAP_GOES_HERE__
};
"""


def template(keyboard):
    """Returns the `keymap.c` template for a keyboard.

    If a template exists in `keyboards/<keyboard>/templates/keymap.c` that
    text will be used instead of `DEFAULT_KEYMAP_C`.

    Args:
        keyboard
            The keyboard to return a template for.
    """
    template_name = 'keyboards/%s/templates/keymap.c' % keyboard

    if os.path.exists(template_name):
        with open(template_name, 'r') as fd:
            return fd.read()

    return DEFAULT_KEYMAP_C


def generate(keyboard, layout, layers):
    """Returns a keymap.c for the specified keyboard, layout, and layers.

    Args:
        keyboard
            The name of the keyboard

        layout
            The LAYOUT macro this keymap uses.

        layers
            An array of arrays describing the keymap. Each item in the inner array should be a string that is a valid QMK keycode.
    """
    layer_txt = []
    for layer_num, layer in enumerate(layers):
        if layer_num != 0:
            layer_txt[-1] = layer_txt[-1] + ','
        layer_keys = ', '.join(layer)
        layer_txt.append('\t[%s] = %s(%s)' % (layer_num, layout, layer_keys))

    keymap = '\n'.join(layer_txt)
    keymap_c = template(keyboard)

    return keymap_c.replace('__KEYMAP_GOES_HERE__', keymap)


def write(keyboard, keymap, layout, layers):
    """Generate the `keymap.c` and write it to disk.

    Returns the filename written to.

    Args:
        keyboard
            The name of the keyboard

        keymap
            The name of the keymap

        layout
            The LAYOUT macro this keymap uses.

        layers
            An array of arrays describing the keymap. Each item in the inner array should be a string that is a valid QMK keycode.
    """
    keymap_c = generate(keyboard, layout, layers)
    keymap_path = qmk.path.keymap(keyboard)
    keymap_dir = os.path.join(keymap_path, keymap)
    keymap_file = os.path.join(keymap_dir, 'keymap.c')

    if not os.path.exists(keymap_dir):
        os.makedirs(keymap_dir)

    with open(keymap_file, 'w') as keymap_fd:
        keymap_fd.write(keymap_c)

    return keymap_file

def find_keymaps(base_path, revision = "", community = False):
    """ Find the available keymaps for a keyboard and revision pair.

    Args:
        base_path: The base path of the keyboard.

        revision: The keyboard's revision.

        community: Set to True for the layouts under layouts/community.

    Returns:
        a set with the keymaps's names
    """
    path_wildcard = os.path.join(base_path, "**", "keymap.c")
    if community:
        path_regex = re.compile(r"^" + re.escape(base_path) + "(\S+)" + os.path.sep + "keymap\.c")
    else:
        path_regex = re.compile(r"^" + re.escape(base_path) + "(?:" + re.escape(revision) + os.path.sep + ")?keymaps" + os.path.sep + "(\S+)" + os.path.sep + "keymap\.c")
    names = [path_regex.sub(lambda name: name.group(1), path) for path in glob.iglob(path_wildcard, recursive = True) if path_regex.search(path)]
    return set(names)

def list_keymaps(keyboard_name):
    """ List the available keymaps for a keyboard.

    Args:
        keyboard_name: the keyboards full name with vendor and revision if necessary, example: clueboard/66/rev3

    Returns:
        a set with the names of the available keymaps
    """
    if os.path.sep in keyboard_name:
        keyboard, revision = os.path.split(os.path.normpath(keyboard_name))
    else:
        keyboard = keyboard_name
        revision = ""

    # parse all the rules.mk files for the keyboard
    rules_mk = qmk.makefile.get_rules_mk(keyboard, revision)
    names = set()

    if rules_mk:
        # get the keymaps from the keyboard's directory
        kb_base_path = os.path.join(os.getcwd(), "keyboards", keyboard) + os.path.sep
        names = find_keymaps(kb_base_path, revision)

        # if community layouts are supported, get them
        if "LAYOUTS" in rules_mk:
            for layout in rules_mk["LAYOUTS"]["value"].split():
                cl_base_path = os.path.join(os.getcwd(), "layouts", "community", layout) + os.path.sep
                names = names.union(find_keymaps(cl_base_path, revision, community = True))

    return sorted(names)
