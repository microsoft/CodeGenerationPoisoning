import yaml
import json


def create_json(yaml_file_path):
    with open(yaml_file_path, "r") as f:
        json_obj = yaml.safe_load(f.read())
        

    model_configuration = {}
    MODEL_ID_URI = "https://w3id.org/okn/i/mint/"
    setup = False
    if "setup" in json_obj:
        setup = True


    modelName = ""
    if "modelName" in json_obj:
        modelName = json_obj["modelName"]

    for key, value in json_obj.items():
        if setup:
            model_configuration["type"] = ["ModelConfigurationSetup"]
        else:
            model_configuration["type"] = ["ModelConfiguration"]

        if key == "modelName":
            model_configuration["id"] = MODEL_ID_URI + value
        elif key == "modelVersion":
            model_configuration["hasVersion"] = [MODEL_ID_URI + modelName + "_" + value]
        elif key == "shortName":
            model_configuration["label"] = [value]
        elif key == "description":
            model_configuration["description"] = value
        elif key == "hasComponentLocation":
            model_configuration["hasComponentLocation"] = value
        elif key == "hasImplementationScriptLocation":
            model_configuration["hasImplementationScriptLocation"] = value
        elif key == "keywords":
            model_configuration["keywords"] = value
        elif key == "hasModelCategory":
            model_configuration["hasModelCategory"] = value
        elif key == "author" or key=="contributor":
            model_configuration[key] = []
            for each_value in value:
                if "type" in each_value:
                    organisation = {}
                    pass
                else:
                    author = {}
                    for input_key, input_value in each_value.items():
                        author["type"] = ["Person"]
                        if input_key == "name":
                            author["label"] = [input_value]
                        elif input_key == "email":
                            author["email"] = [input_value]
                model_configuration[key].append(author)
        elif key == "hasInput" or key == "hasOutput":
            model_configuration[key] = []
            for each_value in value:
                has_input = {}
                for input_key, input_value in each_value.items():
                    has_input["hasDimensionality"] = [0]
                    if setup and input_key == "hasValue":
                        has_input["hasFixedResource"] = []
                        for many_values in input_value:
                            has_fixed_source = {}
                            has_fixed_source["type"] = ["SampleResource"]
                            for inp_key, inp_value in many_values.items():
                                if inp_key == "short_name":
                                    has_fixed_source["label"] = [inp_value]
                                elif inp_key == "description":
                                    has_fixed_source["description"] = inp_value
                                elif inp_key == "url":
                                    has_fixed_source["value"] = [inp_value]
                                elif inp_key == "datacatalogId":
                                    has_fixed_source["dataCatalogIdentifier"] = [inp_value]
                            has_input["hasFixedResource"].append(has_fixed_source)
                    elif input_key == "short_name":
                        has_input["label"] = [input_value]
                    elif input_key == "description":
                        has_input["description"] = input_value
                    elif input_key == "position":
                        has_input["position"] = [input_value]
                    elif input_key == "type":
                        has_input["type"] = input_value
                        has_input["type"].append("DatasetSpecification")
                    elif input_key == "hasDimensionality":
                        has_input["hasDimensionality"] = [input_value]
                    elif input_key == "hasFormat":
                        has_input["hasFormat"] = [input_value]
                    elif input_key == "variables":
                        variable_presentation = []
                        for each_presentation in input_value: 
                            has_presentation = {}
                            for input_presentation, presentation_value in each_presentation.items():
                                has_presentation["type"] = ["VariablePresentation"]
                                if input_presentation == "short_name":
                                    has_presentation["label"] = [presentation_value]
                                elif input_presentation == "description":
                                    has_presentation["description"] = presentation_value
                                elif input_presentation == "hasLongName":
                                    has_presentation["hasLongName"] = [presentation_value]
                                elif input_presentation == "hasShortName":
                                    has_presentation["hasShortName"] = [presentation_value]
                                elif input_presentation == "usesUnit":
                                    has_presentation["usesUnit"] = []
                                    has_presentation["usesUnit"].append({"label": [presentation_value]})
                                elif input_presentation == "hasStandardName":
                                    standard_variable = []
                                    if isinstance(presentation_value, list):
                                        for each_standard_variable in presentation_value:
                                            has_standard_variable = {}
                                            for input_standard_variable, standard_variable_value in each_standard_variable.items():
                                                has_standard_variable["type"] = ["StandardVariable"] 
                                                if input_standard_variable == "":
                                                    pass
                                    elif isinstance(presentation_value, str):
                                        has_standard_variable = {}
                                        has_standard_variable["label"] = [presentation_value]
                                        has_standard_variable["type"] = ["StandardVariable"]
                                        standard_variable.append(has_standard_variable)
                                    has_presentation["hasStandardVariable"] = standard_variable
                            variable_presentation.append(has_presentation)
                        has_input["hasPresentation"] = variable_presentation
                model_configuration[key].append(has_input)
        elif key == "hasParameter":
            model_configuration[key] = []
            for each_value in value:
                has_parameter = {}
                for input_parameter, parameter_value in each_value.items():
                    has_parameter["type"] = ["Parameter"]
                    if input_parameter == "short_name":
                        has_parameter["label"] = [parameter_value]
                    elif input_parameter == "description":
                        has_parameter["description"] = parameter_value
                    elif input_parameter == "usesUnit":
                         has_parameter["usesUnit"] = []
                         has_parameter["usesUnit"].append({"label": [parameter_value]})
                    elif input_parameter == "dataType":
                        has_parameter["hasDataType"] = [parameter_value]
                    elif input_parameter == "defaultValue":
                        has_parameter["hasDefaultValue"] = [parameter_value]
                    elif input_parameter == "maxValue":
                        has_parameter["hasMaximumAcceptedValue"] = [parameter_value]
                    elif input_parameter == "minValue":
                        has_parameter["hasMinimumAcceptedValue"] = [parameter_value]
                model_configuration[key].append(has_parameter)
        elif key == "hasGrid":
            model_configuration[key] = []
            for each_value in value:
                has_grid = {}
                for input_parameter, parameter_value in each_value.items():
                    has_grid["type"] = ["Grid"]
                    if input_parameter == "short_name":
                        has_grid["label"] = [parameter_value]
                    elif input_parameter == "description":
                        has_grid["description"] = parameter_value
                    elif input_parameter == "hasDimension":
                        has_grid["hasDimension"] = [parameter_value]
                    elif input_parameter == "hasShape":
                        has_grid["hasShape"] = [parameter_value]
                    elif input_parameter == "hasSpatialResolution":
                        has_grid["hasSpatialResolution"] = [parameter_value]
                model_configuration[key].append(has_grid)
        elif key == "hasRegion":
            model_configuration[key] = []
            for each_value in value:
                has_region = {}
                for input_parameter, parameter_value in each_value.items():
                    has_region["type"] = ["Region"]
                    if input_parameter == "short_name":
                        has_region["label"] = [parameter_value]
                    elif input_parameter == "description":
                        has_region["description"] = parameter_value
                model_configuration[key].append(has_region)
        elif key == "hasSourceCode":
            model_configuration[key] = []
            for each_value in value:
                has_source_code = {}
                for input_parameter, parameter_value in each_value.items():
                    has_source_code["type"] = ["SourceCode"]
                    if input_parameter == "short_name":
                        has_source_code["label"] = [parameter_value]
                    elif input_parameter == "description":
                        has_source_code["description"] = parameter_value
                    elif input_parameter == "codeRepository":
                        has_source_code["codeRepository"] = [parameter_value]
                    elif input_parameter == "programmingLanguage":
                        has_source_code["programmingLanguage"] = parameter_value
                model_configuration[key].append(has_source_code)
        elif key == "hasOutputTimeInterval":
            model_configuration[key] = []
            for each_value in value:
                has_output_time_interval = {}
                for input_parameter, parameter_value in each_value.items():
                    has_output_time_interval["type"] = ["TimeInterval"]
                    if input_parameter == "short_name":
                        has_output_time_interval["label"] = [parameter_value]
                    elif input_parameter == "description":
                        has_output_time_interval["description"] = parameter_value
                    elif input_parameter == "codeRepository":
                        has_output_time_interval["codeRepository"] = [parameter_value]
                    elif input_parameter == "programmingLanguage":
                        has_output_time_interval["programmingLanguage"] = parameter_value

                model_configuration[key].append(has_output_time_interval)
        elif key == "hasProcess":
            model_configuration[key] = []
            for each_value in value:
                has_process = {}
                has_process["label"] = [each_value]
                has_process["type"] = ["Process"]
                model_configuration[key].append(has_process)
        elif key == "hasSoftwareImage":
            model_configuration[key] = []
            model_configuration[key].append({"label": [value]})

    return model_configuration
