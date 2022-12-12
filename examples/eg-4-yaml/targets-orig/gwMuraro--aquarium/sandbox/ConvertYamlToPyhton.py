import yaml
with open("config.yaml") as stream:
    #test de lecture 
    try:
        data=yaml.safe_load(stream)
        #exemple d'affichage
        print(data["gupy"]["argent"])
        #print(data)
    except yaml.YAMLError as exc:
        print(exc)
