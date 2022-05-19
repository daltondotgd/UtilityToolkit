import unreal


##
# Actions to be performed on a per-texture basis
##

# A base class for actions
class Action:
    def execute(self, material, expression):
        pass

# Adds a sampler and connects the desired output to the desired material property pin
class CreateConnection(Action):
    def __init__(self, output_name, material_property):
        self.output_name = output_name
        self.material_property = material_property

    def execute(self, material, expression, y_pos):
        unreal.MaterialEditingLibrary.connect_material_property(expression, self.output_name, self.material_property)

# Same as CreateConnection, but a Multiply node is also generated so the color value is scaled by the given factor
class CreateConnectionScaled(CreateConnection):
    def __init__(self, output_name, material_property, scale):
        self.output_name = output_name
        self.material_property = material_property
        self.scale = scale

    def execute(self, material, expression, y_pos):
        multiply_node = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionMultiply, -250, y_pos)
        multiply_node.set_editor_property('ConstB', self.scale)
        unreal.MaterialEditingLibrary.connect_material_expressions(expression, self.output_name, multiply_node, 'A')
        unreal.MaterialEditingLibrary.connect_material_property(multiply_node, '', self.material_property)

# Sets any available property on the material asset
class SetProperty(Action):
    def __init__(self, property, value):
        self.property = property
        self.value = value

    def execute(self, material, expression, y_pos):
        material.set_editor_property(self.property, self.value)

# Sets the sampler type for the texture sample
class SetSamplerType(Action):
    def __init__(self, sampler_type):
        self.sampler_type = sampler_type

    def execute(self, material, expression, y_pos):
        expression.set_editor_property('sampler_type', self.sampler_type)

##
# This dictionary assigns the given texture type names (found in suffixes, for ex. T_TextureName_D - D means it's a Diffuse texture)
# to the different actions that should be performed to properly set it up in the material.
##

actions = {
    'DA': [
        CreateConnection('RGB', unreal.MaterialProperty.MP_BASE_COLOR),
        CreateConnection('A', unreal.MaterialProperty.MP_OPACITY),
        SetProperty('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    ],
    'D': [
        CreateConnection('RGB', unreal.MaterialProperty.MP_BASE_COLOR)
    ],
    'AO': [
        CreateConnection('R', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
        SetSamplerType(unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    ],
    'A': [
        CreateConnection('R', unreal.MaterialProperty.MP_OPACITY),
        SetSamplerType(unreal.MaterialSamplerType.SAMPLERTYPE_GRAYSCALE),
        SetProperty('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    ],
    'N': [
        CreateConnection('RGB', unreal.MaterialProperty.MP_NORMAL),
        SetSamplerType(unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    ],
    'M': [
        CreateConnection('R', unreal.MaterialProperty.MP_METALLIC),
        SetSamplerType(unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    ],
    'R': [
        CreateConnection('G', unreal.MaterialProperty.MP_ROUGHNESS),
        SetSamplerType(unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    ],
    'S': [
        CreateConnection('B', unreal.MaterialProperty.MP_SPECULAR),
        SetSamplerType(unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    ],
    'E': [
        CreateConnectionScaled('RGB', unreal.MaterialProperty.MP_EMISSIVE_COLOR, 15)
    ],
}

##
# Helper functions
##

# Create a material at a given path
def create_empty_material(name) -> unreal.Material:
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    package_name, asset_name = asset_tools.create_unique_asset_name(name, '')
    if not unreal.EditorAssetLibrary.does_asset_exist(package_name):
        path = package_name.rsplit('/', 1)[0]
        name = package_name.rsplit('/', 1)[1]
        return asset_tools.create_asset(name, path, unreal.Material, unreal.MaterialFactoryNew())
    return unreal.load_asset(package_name)

# Perform actions defined in the 'actions' dictionary. This should result in textures being added properly with respect for required
# or desired settings for certain texture types
def apply_texture(material, texture_name, y_pos):
    sampler = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureSample, -500, y_pos)

    sampler.texture = unreal.load_asset(texture_name)
    texture_suffix = texture_name.rsplit('_', 1)[1]
    for key in actions:
        if key in texture_suffix:
            texture_suffix = texture_suffix.replace(key, '')
            for action in actions[key]:
                action.execute(material, sampler, y_pos)

##
# Create material from selected textures
##

def create_material_from_textures(name):
    material = create_empty_material(name)

    selected_assets = unreal.EditorUtilityLibrary.get_selected_assets()
    y_pos = 0
    for asset in selected_assets:
        if isinstance(asset, unreal.Texture):
            apply_texture(material, asset.get_path_name(), y_pos)
            y_pos += 250

    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_asset(material.get_path_name(), True)
    
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.open_editor_for_assets([material])
