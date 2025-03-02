import inspect
from importlib import import_module
from os.path import basename
from pathlib import Path
from typing import Hashable

import sims4.tuning.serialization
from sims4.commands import CheatOutput, Command, CommandType
from sims4.log import Logger
from sims4.tuning.instances import TunedInstanceMetaclass
from sims4.tuning.tunable_base import TunableBase
from sims4.tuning.tunable_perf import TuningAttrCleanupHelper

logger = Logger("export_tdesc")


def inject(target_object, target_function_name):
    def decorator(injected_function):
        original_function = getattr(target_object, target_function_name)
        setattr(
            target_object,
            target_function_name,
            lambda *args, **kwargs: injected_function(original_function, *args, **kwargs),
        )
        return injected_function

    return decorator


# Usually the game purges some attributes after it's finished loading
# We need that data so we prevent it from being cleaned
# This is probably bad for performance
@inject(TuningAttrCleanupHelper, "perform_cleanup")
def _(*_):
    return


# ### Begin "bug"fix for EA code ###
# *Loads* of AttributeErrors are thrown unless I do this
# Apparently the production code is WILDLY different to the dev code here
# We need to add these attrs to TunableBase:
tunable_injected_attrs = (
    "name",
    "description",
    "tuning_filter",
    "group",
    "_deprecated",
    "_category",
    "needs_tuning",
    "export_modes",
    "_allow_empty",
    "_display_name",
    "minlength",
    "maxlength",
)


# TunableBase has __slots__, so we can't add any attributes to instances,
# i.e. we can't store any data in instances. This is a bit of a dirty hack, but it works:
class InjectableAttribute:
    """
    Descriptor that can store per-instance data in itself. Can be injected as a
    new attribute into classes that don't have a ``__dict__``.

    Will never raise AttributeError, but instead return ``None``.
    """

    __slots__ = "_storage"

    def __init__(self):
        self._storage = {}

    def __get__(self, instance: Hashable, owner):
        return self._storage.get(instance, None)

    def __set__(self, instance: Hashable, value):
        if value is None and instance in self._storage:
            del self._storage[instance]
        else:
            self._storage[instance] = value


# kwargs for __init__ are spelled without the underscore:
# deprecated <- _deprecated
tunable_init_arg_map = {attr.strip("_"): attr for attr in tunable_injected_attrs}

# Inject descriptors into class
for attr in tunable_injected_attrs:
    if not hasattr(TunableBase, attr):
        setattr(TunableBase, attr, InjectableAttribute())


# The dev version of __init__ accepts many of the missing attrs as kwargs:
@inject(TunableBase, "__init__")
def _(orig, self, *args, **kwargs):
    orig(self, *args, **kwargs)
    for arg_name, value in kwargs.items():
        if arg_name in tunable_init_arg_map:
            setattr(self, tunable_init_arg_map[arg_name], value)


# ### End bugfix for EA code ###


@Command("export_tdesc", command_type=CommandType.Live)
def _(module_name="", cls_name="", _connection=None) -> None:
    output = CheatOutput(_connection)
    if not module_name:
        output(
            """
        Usage:
        export_tdesc my.module
        export_tdesc my.module MyClass
        """
        )
        return
    success = False
    output(f"Exporting TDESC for {module_name}.{cls_name}...")

    def export_module_rec(module):
        nonlocal success
        for _, member in inspect.getmembers(module):
            if inspect.getmodule(member) is not module:
                continue
            elif inspect.ismodule(member):
                # this doesn't really work as i had hoped, i think it just never recurses
                # single modules work fine tho
                export_module_rec(module)
            elif isinstance(member, TunedInstanceMetaclass):
                if sims4.tuning.serialization.export_class(
                    member,
                    export_path.joinpath(basename(member.tuning_manager.PATH)),
                    member.tuning_manager.TYPE,
                ):
                    success = True
                else:
                    raise Exception(f"Failed to export {member}")
        return success

    try:
        export_path = next(
            path for path in Path(__file__).parents if path.name.lower() == "the sims 4"
        ).joinpath("Descriptions")

        module = import_module(module_name)
        # I haven't tested this, but maybe running reload_module(module) here would make this
        # work for vanilla tunables as well

        if cls_name:
            cls = next(
                (v for k, v in inspect.getmembers(module) if k.lower() == cls_name),
                None,
            )
            if cls:
                if not sims4.tuning.serialization.export_class(
                    cls,
                    export_path.joinpath(basename(cls.tuning_manager.PATH)),
                    cls.tuning_manager.TYPE,
                ):
                    output("Error during TDESC export")
                    return
            else:
                output("Could not find class in module.")
                return
        else:
            if not export_module_rec(module):
                output(f"No tunables found in {module}")
                return
        output(f"Done. Files have been saved to {export_path}.")
    except Exception as e:
        output(f"Error: {e}")
