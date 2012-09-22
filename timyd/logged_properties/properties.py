class Property(object):
    """This class represents a property in a class.

    It is autodiscovered and provide a convenient Python-interface to use a
    BinaryLog; you can just access and change the properties on an object.
    """

    def __init__(self, name):
        self._name = name

    def __get__(self, obj, type=None):
        return obj._log.get_property(self._name)

    def __set__(self, obj, value):
        if obj._log.get_property(self._name) != value:
            obj._log.set_property(self._name, value)



class StringProperty(Property):
    """Property with string values.
    """

    def __set__(self, obj, value):
        if isinstance(value, str):
            Property.__set__(self, obj, value)
        else:
            raise TypeError('StringProperty expected str, got %s' % (
                    type(value)))


class UnicodeProperty(Property):
    """Property with unicode values.
    """

    def __get__(self, obj, type=None):
        v = Property.__get__(self, obj)
        return v.decode('utf-8')

    def __set__(self, obj, value):
        if isinstance(value, unicode):
            Property.__set__(self, obj, value.encode('utf-8'))
        else:
            raise TypeError('UnicodeProperty expected unicode, got %s' % (
                    type(value)))


class IntegerProperty(Property):
    """Property with integer values.
    """

    def __set__(self, obj, value):
        if isinstance(value, (int, long)):
            Property.__set__(self, obj, value)
        else:
            raise TypeError('IntegerProperty expected int or long, got %s' % (
                    type(value)))


class EnumProperty(StringProperty):
    """Property with a limited set of allowed values.
    """

    def __init__(self, name, values):
        StringProperty.__init__(self, name)
        self._values = values

    def __set__(self, obj, value):
        if value in self._values:
            StringProperty.__set__(self, obj, value)
        else:
            raise TypeError('EnumProperty received unknown value %r' % (
                    value,))
