import yaml
print(help(yaml))


"""
Help on package yaml:

NAME
    yaml

PACKAGE CONTENTS
    composer
    constructor
    cyaml
    dumper
    emitter
    error
    events
    loader
    nodes
    parser
    reader
    representer
    resolver
    scanner
    serializer
    tokens

CLASSES
    builtins.object
        YAMLObject
    builtins.type(builtins.object)
        YAMLObjectMetaclass
    
    class YAMLObject(builtins.object)
     |  An object that can dump itself to a YAML stream
     |  and load itself from a YAML stream.
     |  
     |  Class methods defined here:
     |  
     |  from_yaml(loader, node) from YAMLObjectMetaclass
     |      Convert a representation node to a Python object.
     |  
     |  to_yaml(dumper, data) from YAMLObjectMetaclass
     |      Convert a Python object to a representation node.
     |  
     |  ----------------------------------------------------------------------
     |  Data and other attributes defined here:
     |  
     |  yaml_dumper = <class 'yaml.dumper.Dumper'>
     |  
     |  
     |  yaml_flow_style = None
     |  
     |  yaml_loader = <class 'yaml.loader.Loader'>
     |  
     |  
     |  yaml_tag = None
    
    class YAMLObjectMetaclass(builtins.type)
     |  The metaclass for YAMLObject.
     |  
     |  Method resolution order:
     |      YAMLObjectMetaclass
     |      builtins.type
     |      builtins.object
     |  
     |  Methods defined here:
     |  
     |  __init__(cls, name, bases, kwds)
     |      Initialize self.  See help(type(self)) for accurate signature.
     |  
     |  ----------------------------------------------------------------------
     |  Methods inherited from builtins.type:
     |  
     |  __call__(self, /, *args, **kwargs)
     |      Call self as a function.
     |  
     |  __delattr__(self, name, /)
     |      Implement delattr(self, name).
     |  
     |  __dir__(...)
     |      __dir__() -> list
     |      specialized __dir__ implementation for types
     |  
     |  __getattribute__(self, name, /)
     |      Return getattr(self, name).
     |  
     |  __instancecheck__(...)
     |      __instancecheck__() -> bool
     |      check if an object is an instance
     |  
     |  __new__(*args, **kwargs) from builtins.type
     |      Create and return a new object.  See help(type) for accurate signature.
     |  
     |  __prepare__(...) from builtins.type
     |      __prepare__() -> dict
     |      used to create the namespace for the class statement
     |  
     |  __repr__(self, /)
     |      Return repr(self).
     |  
     |  __setattr__(self, name, value, /)
     |      Implement setattr(self, name, value).
     |  
     |  __sizeof__(...)
     |      __sizeof__() -> int
     |      return memory consumption of the type object
     |  
     |  __subclasscheck__(...)
     |      __subclasscheck__() -> bool
     |      check if a class is a subclass
     |  
     |  __subclasses__(...)
     |      __subclasses__() -> list of immediate subclasses
     |  
     |  mro(...)
     |      mro() -> list
     |      return a type's method resolution order
     |  
     |  ----------------------------------------------------------------------
     |  Data descriptors inherited from builtins.type:
     |  
     |  __abstractmethods__
     |  
     |  __dict__
     |  
     |  __text_signature__
     |  
     |  ----------------------------------------------------------------------
     |  Data and other attributes inherited from builtins.type:
     |  
     |  __base__ = <class 'type'>
     |      type(object_or_name, bases, dict)
     |      type(object) -> the object's type
     |      type(name, bases, dict) -> a new type
     |  
     |  __bases__ = (<class 'type'>,)
     |  
     |  __basicsize__ = 864
     |  
     |  __dictoffset__ = 264
     |  
     |  __flags__ = 2148292097
     |  
     |  __itemsize__ = 40
     |  
     |  __mro__ = (<class 'yaml.YAMLObjectMetaclass'>, <class 'type'>, <class ...
     |  
     |  __weakrefoffset__ = 368

FUNCTIONS
    add_constructor(tag, constructor, Loader=<class 'yaml.loader.Loader'>)
        Add a constructor for the given tag.
        Constructor is a function that accepts a Loader instance
        and a node object and produces the corresponding Python object.
    
    add_implicit_resolver(tag, regexp, first=None, Loader=<class 'yaml.loader.Loader'>, Dumper=<class 'yaml.dumper.Dumper'>)
        Add an implicit scalar detector.
        If an implicit scalar value matches the given regexp,
        the corresponding tag is assigned to the scalar.
        first is a sequence of possible initial characters or None.
    
    add_multi_constructor(tag_prefix, multi_constructor, Loader=<class 'yaml.loader.Loader'>)
        Add a multi-constructor for the given tag prefix.
        Multi-constructor is called for a node if its tag starts with tag_prefix.
        Multi-constructor accepts a Loader instance, a tag suffix,
        and a node object and produces the corresponding Python object.
    
    add_multi_representer(data_type, multi_representer, Dumper=<class 'yaml.dumper.Dumper'>)
        Add a representer for the given type.
        Multi-representer is a function accepting a Dumper instance
        and an instance of the given data type or subtype
        and producing the corresponding representation node.
    
    add_path_resolver(tag, path, kind=None, Loader=<class 'yaml.loader.Loader'>, Dumper=<class 'yaml.dumper.Dumper'>)
        Add a path based resolver for the given tag.
        A path is a list of keys that forms a path
        to a node in the representation tree.
        Keys can be string values, integers, or None.
    
    add_representer(data_type, representer, Dumper=<class 'yaml.dumper.Dumper'>)
        Add a representer for the given type.
        Representer is a function accepting a Dumper instance
        and an instance of the given data type
        and producing the corresponding representation node.
    
    compose(stream, Loader=<class 'yaml.loader.Loader'>)
        Parse the first YAML document in a stream
        and produce the corresponding representation tree.
    
    compose_all(stream, Loader=<class 'yaml.loader.Loader'>)
        Parse all YAML documents in a stream
        and produce corresponding representation trees.
    
    dump(data, stream=None, Dumper=<class 'yaml.dumper.Dumper'>, **kwds)
        Serialize a Python object into a YAML stream.
        If stream is None, return the produced string instead.
    
    dump_all(documents, stream=None, Dumper=<class 'yaml.dumper.Dumper'>, default_style=None, default_flow_style=None, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None, encoding=None, explicit_start=None, explicit_end=None, version=None, tags=None)
        Serialize a sequence of Python objects into a YAML stream.
        If stream is None, return the produced string instead.
    
    emit(events, stream=None, Dumper=<class 'yaml.dumper.Dumper'>, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None)
        Emit YAML parsing events into a stream.
        If stream is None, return the produced string instead.
    
    load(stream, Loader=<class 'yaml.loader.Loader'>)
        Parse the first YAML document in a stream
        and produce the corresponding Python object.
    
    load_all(stream, Loader=<class 'yaml.loader.Loader'>)
        Parse all YAML documents in a stream
        and produce corresponding Python objects.
    
    parse(stream, Loader=<class 'yaml.loader.Loader'>)
        Parse a YAML stream and produce parsing events.
    
    safe_dump(data, stream=None, **kwds)
        Serialize a Python object into a YAML stream.
        Produce only basic YAML tags.
        If stream is None, return the produced string instead.
    
    safe_dump_all(documents, stream=None, **kwds)
        Serialize a sequence of Python objects into a YAML stream.
        Produce only basic YAML tags.
        If stream is None, return the produced string instead.
    
    safe_load(stream)
        Parse the first YAML document in a stream
        and produce the corresponding Python object.
        Resolve only basic YAML tags.
    
    safe_load_all(stream)
        Parse all YAML documents in a stream
        and produce corresponding Python objects.
        Resolve only basic YAML tags.
    
    scan(stream, Loader=<class 'yaml.loader.Loader'>)
        Scan a YAML stream and produce scanning tokens.
    
    serialize(node, stream=None, Dumper=<class 'yaml.dumper.Dumper'>, **kwds)
        Serialize a representation tree into a YAML stream.
        If stream is None, return the produced string instead.
    
    serialize_all(nodes, stream=None, Dumper=<class 'yaml.dumper.Dumper'>, canonical=None, indent=None, width=None, allow_unicode=None, line_break=None, encoding=None, explicit_start=None, explicit_end=None, version=None, tags=None)
        Serialize a sequence of representation trees into a YAML stream.
        If stream is None, return the produced string instead.

DATA
    __with_libyaml__ = False

VERSION
    3.13

FILE
    /usr/local/lib/python3.6/site-packages/yaml/__init__.py


None
[Finished in 0.4s]

"""











