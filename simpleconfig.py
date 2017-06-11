from panda3d.core import *
load_prc_file_data("", "notify-level-prc error")

class MetaConfig(type):
    """Metaclass for the config class, actually implements all the logic.
    This is used to make __getitem__ and __setitem__ static class methods
    """
    def __getitem__(cls, key):
        value_type=ConfigVariable(key).get_value_type()
        if value_type == ConfigVariable.VT_undefined:
            return ConfigVariable(key).get_string_value()
        elif value_type == ConfigVariable.VT_list:
            return  [i for i in ConfigVariableList(key)]
        elif value_type == ConfigVariable.VT_string:
            return ConfigVariableString(key).get_value()
        elif value_type == ConfigVariable.VT_filename:
            return ConfigVariableFilename(key).get_value()
        elif value_type == ConfigVariable.VT_bool:
            return ConfigVariableBool(key).get_value()
        elif value_type == ConfigVariable.VT_int:
            num_words=ConfigVariableInt(key).get_num_words()
            if num_words >1:
                return [ConfigVariableInt(key).get_word(i) for i in range(num_words)]
            else:
                return ConfigVariableInt(key).get_value()
        elif value_type == ConfigVariable.VT_double:
            return ConfigVariableDouble(key).get_value()
        elif value_type == ConfigVariable.VT_enum:
            return ConfigVariable(key).get_string_value()
        elif value_type == ConfigVariable.VT_search_path:
            return ConfigVariableSearchPath(key).get_value()
        elif value_type == ConfigVariable.VT_int64:
            return ConfigVariableInt64(key).get_value()
        elif value_type == ConfigVariable.VT_color:
            return ConfigVariableColor(key).get_value()
        return ConfigVariable(key).get_string_value()

    def __setitem__(cls, key, value):
        value_type=ConfigVariable(key).get_value_type()
        if value_type == ConfigVariable.VT_undefined:
            ConfigVariable(key).set_string_value(value)
        elif value_type == ConfigVariable.VT_list:
            raise TypeError("'panda3d.core.ConfigVariableList' object does not support item assignment")
        elif value_type == ConfigVariable.VT_string:
            ConfigVariableString(key).set_value(value)
        elif value_type == ConfigVariable.VT_filename:
            ConfigVariableFilename(key).set_value(value)
        elif value_type == ConfigVariable.VT_bool:
            ConfigVariableBool(key).set_value(value)
        elif value_type == ConfigVariable.VT_int:
            ConfigVariableInt(key).set_value(value)
        elif value_type == ConfigVariable.VT_double:
            ConfigVariableDouble(key).set_value(value)
        elif value_type == ConfigVariable.VT_enum:
            ConfigVariable(key).set_string_value(value)
        elif value_type == ConfigVariable.VT_search_path:
            ConfigVariableSearchPath(key).set_value(value)
        elif value_type == ConfigVariable.VT_int64:
            ConfigVariableInt64(key).set_value(value)
        elif value_type == ConfigVariable.VT_color:
            ConfigVariableColor(key).set_value(value)

    def __contains__(cls, item):
        return ConfigVariable(item).hasValue()

class SimpleConfig(object, metaclass=MetaConfig):
    """This class is a wrapper for Panda3D ConfigVariable*
    with dict like interface (SimpleConfig['some_config_name']=some_value)
    """
    pass
