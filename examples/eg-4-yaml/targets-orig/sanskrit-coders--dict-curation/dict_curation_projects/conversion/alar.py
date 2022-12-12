import yaml
from dict_curation import babylon

def dump_babylon(dict, output_path):
  with open(output_path, "w") as outfile:
    for item in dict:
      headword = item["entry"]
      headword_intro = "%s %s" % (item["phone"], item["origin"])
      entries = ["%s<br>%s" % (definition["type"], definition["entry"]) for definition in item["defs"]]
      babylon_entry = "%s<br><br>%s" % (headword_intro, "<br><br>".join(entries))
      outfile.write("%s\n%s\n\n" % (headword, babylon_entry))


if __name__ == '__main__':
  base_path = "/home/vvasuki/indic-dict/stardict-kannada/kn-head/alar/alar"
  with open(base_path + ".yml.local") as yml_file:
    dict = yaml.load(yml_file, Loader=yaml.BaseLoader)
    dump_babylon(dict, output_path=base_path + ".babylon")