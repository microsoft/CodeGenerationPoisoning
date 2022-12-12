"""Common functions used by various Genesys tools"""
import os

CHARACTERISTICS = [ 'BR', 'AG', 'INT', 'CUN', 'WILL', 'PR']


def genesys_symbol(s, color="#000000"):
    return "<font name='Genesys' color='%s'>%s</font>" % (color, s)

GENESYS_DICE = {
    "boost":        ("j", "#72cddc"),
    "ability":      ("k", "#02a652"),
    "proficiency":  ("l",'#fff201'),
    "setback":      ("j",'#000000'),
    "difficulty":   ("k",'#6c2a84'),
    "challenge":    ("l",'#7d1821')
}

SUCCESS_SYMBOL = genesys_symbol("s")
FAILURE_SYMBOL = genesys_symbol("f")
ADVANTAGE_SYMBOL = genesys_symbol("a")
THREAT_SYMBOL = genesys_symbol("h")
TRIUMPH_SYMBOL = genesys_symbol("t")
DESPAIR_SYMBOL = genesys_symbol("d")

BOOST_SYMBOL = genesys_symbol("j", "#72cddc")
ABILITY_SYMBOL = genesys_symbol("k", "#02a652")
PROFICIENCY_SYMBOL = genesys_symbol("l",'#fff201')
SETBACK_SYMBOL = genesys_symbol("j",'#000000')
DIFFICULTY_SYMBOL = genesys_symbol("k",'#6c2a84')
CHALLENGE_SYMBOL = genesys_symbol("l",'#7d1821')

COMBAT_SYMBOL = genesys_symbol("c")
SOCIAL_SYMBOL = genesys_symbol("p")
GENERAL_SYMBOL = genesys_symbol("g")

SYMBOL_CODES = {
    '[BO]': BOOST_SYMBOL,
    '[SB]': SETBACK_SYMBOL,
    '[AB]': ABILITY_SYMBOL,
    '[DI]': DIFFICULTY_SYMBOL,
    '[PR]': PROFICIENCY_SYMBOL,
    '[CH]': CHALLENGE_SYMBOL,

    '[SU]': SUCCESS_SYMBOL,
    '[AD]': ADVANTAGE_SYMBOL,
    '[TR]': TRIUMPH_SYMBOL,
    '[FA]': FAILURE_SYMBOL,
    '[TH]': THREAT_SYMBOL,
    '[DE]': DESPAIR_SYMBOL,
}

def humanize(s):
    return s.replace("_", " ").title()

def format_modifier(value):
    return str(value) if (value < 0) else "+" + str(value)

def batch_list(list, batch_size):
    return [ list[i:i + batch_size] for i in range(0, len(list), batch_size) ]

def resource_path(filename, root=None, directory="resources", ext=None):
    """Returns the full pathname of the specified file in a resource directory"""
    root = __file__ if root==None else root
    root = os.path.dirname(root) if not os.path.isdir(root) else root

    while root != os.path.dirname(root):
        path = os.path.join(root, directory, filename)
        if os.path.isfile(path):
            return os.path.abspath(path)
        if ext is not None:
            path = f"{path}.{ext}"
        if os.path.isfile(path):
            return os.path.abspath(path)
        root = os.path.dirname(root)
    raise FileNotFoundError(f"Resource not found: {filename}")

def resolve_resources(filenames, root=None, directory="resources", ext=None):
    filenames = [filenames] if isinstance(filenames, str) else filenames

    return [resource_path(f, root=root, directory=directory, ext=ext) for f in filenames]

def load_data(files, filter=None, root=__file__, directory="data"):
    """Read YAML file and return list containing the data"""
    import yaml
    files = resolve_resources(files, root=root, directory=directory, ext="yaml")
    records = []
    for yamlfile in files:
        with open(yamlfile) as file:
            items = yaml.safe_load(file)
            items = [items] if isinstance(items, dict) else items
            records += items

    if filter != None:
        records = [ item for item in records if filter(item) ]

    return records

def safe_font(name, name_suffix, directory, suffixes=[], default=None):
    from reportlab.pdfbase.ttfonts import TTFont

    font = None
    qualified_name = name + name_suffix
    for suffix in suffixes:
        file = os.path.join(directory, name + suffix + ".ttf")
        if os.path.isfile(file):
            font = TTFont(qualified_name, file)
            break

    if font is None:
        if default is not None:
            font = default
        elif font == None:
            raise ValueError("Font not found and no default: " + name)
    return (qualified_name, font)

def register_font(name, font):
    from reportlab.pdfbase import pdfmetrics
    pdfmetrics.registerFont(font)
    return name

def register_font_family(name):
    (base_path, ext) = os.path.splitext(name)
    base = os.path.basename(base_path)
    dir = os.path.dirname(base_path)
    from reportlab.pdfbase import pdfmetrics

    (normal, normal_font) = safe_font(base, "", dir, suffixes=[ "-Regular", ""])
    register_font(normal, normal_font)
    bold = register_font(*safe_font(base, 'Bd', dir, suffixes=["-Bold", " Bold"], default=normal_font))
    italic = register_font(*safe_font(base, 'It', dir, suffixes=["-Italic", " Italic"], default=normal_font))
    bold_italic = register_font(*safe_font(base, 'BI', dir, suffixes=["-BoldItalic", " Bold Italic"], default=normal_font))
    pdfmetrics.registerFontFamily(base, normal=normal, bold=bold, italic=italic, boldItalic = bold_italic)

def register_fonts():
    """Register the fonts typically used by Genesys tools."""

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont("genesys", 'C:\\Users\\Semprebon\\Appdata\\local\\microsoft\\windows\\fonts\\GenesysGlyphsAndDice-2.2.ttf'))
    register_font_family('C:\\Users\\Semprebon\\Appdata\\local\\microsoft\\windows\\fonts\\RobotoCondensed.ttf')
    register_font_family('C:\\Windows\\Fonts\\seguisym.ttf')


def translate_symbols(s):
    for code, sym in SYMBOL_CODES.items():
        s = s.replace(code, sym)
    return s


def load_setting(files, root=__file__):
    setting_list = load_data(files, root=root)
    files = []
    for setting in setting_list:
        files.extend(setting.get("files", []))
    if len(files) > 0:
        setting_list.extend(load_data(files, root=root))

    setting = { 'skills': {}, 'archetypes': {}, 'careers': {}, 'talents': {}, 'items': {} }
    for item in setting_list:
        for name, catagory in setting.items():
            if name in item:
                catagory.update(item[name])
    return setting

def scale_to_fit(image_size, space_size):
    src_aspect = image_size[1] / float(image_size[0])
    dest_aspect = space_size[1] / float(space_size[0])
    if dest_aspect > src_aspect:
        return [space_size[0], space_size[1] * src_aspect / dest_aspect]
    else:
        return [space_size[0] * dest_aspect / src_aspect, space_size[1]]

def get_image(path, max_size):
    from reportlab.platypus import Image
    from reportlab.lib import utils
    image = utils.ImageReader(path)
    (w, h) = scale_to_fit(list(image.getSize()), max_size)
    return Image(path, width=w, height=h)

