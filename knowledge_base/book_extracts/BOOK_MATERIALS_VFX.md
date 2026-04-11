# Book Knowledge: Materials & VFX

> Extracted from 1 books. Total 15 relevant sections.

---

## Source: Mastering Technical Art in Unreal Engine (Greg Penninck)

### Adding Panning to Our Additive Master Material (Page 128)

109 
Introductory Materials for VFX 
• We can manipulate, distort and animate Texture UV’s. 
• We can alter the brightness or color of an effect. 
• We can use Dynamic Parameters that connect Unreal’s Niagara Editor to the 
Material Editor. 
Let’s explore these three approaches by modifying our existing VFX Master Materials. 
Panning and UV Distortion 
We are now going to distort our Texture UV’s in the Material M_VFXAdd. To do 
this we are going to use a Panner node which allows us to move textures in the X and 
Y axis. Combining movements with masks can create quite sophisticated distortions 
which can make fat textures look volumetric and 3D. 
Animation in the Material Editor goes alongside Animation in the Niagara Editor 
in Unreal. Not all Particle Systems will require distorted UV’s but what we are about 
to do provides a way to break up the repetition of textures. 
Adding Panning to Our Additive Master Material 
1. In the Content Browser, navigate to the folder Content | Materials | 
Master. 
2. Double click on the Material M_VFXAdd to open the Material Editor. 
3. In the Content Drawer, navigate to Content | Textures | EnergyOrb. 
4. Drag and drop the Texture Particle2 into the Material M_VFXAdd. 
5. Move this Texture Sample to the left of the ParticleTexture Param2D. 
6. Right click in the Material Graph and Search for a Panner Node. Position 
this node to the left of the Particle2 Texture Sample node. 
7. Connect the output pin of the Panner node into the UV input of the Particle2 
Texture Sample node. 
8. Right click in the Material Graph and Search for a Component Mask node. 
Position the Mask (R G ) node in between the Particle2 Texture Sample 
node and the ParticleTexture node. 
9. Connect the RGB output of the Particle2 Texture Sample into the input of 
the Mask (R G ) node. 
10. Connect the output of the Mask (R G ) node to the UV input of the 
ParticleTexture Param 2D node. You will see our ParticleTexture’s node 
preview distort. 
We are now going to add a couple of nodes to create a Mask around our Particle 
Texture’s UVs. The Radial Mask will limit where panning and distortion can take 
place, you can always right click on a node and preview it if you are unsure as to its 
contributions to the Material Graph. When working with Masks, Panners and other 
functions it’s nice to preview what you are doing as you build up your material to 
ensure everything is moving correctly. Let’s now carry on building our Material.

---

### Adding Particle Color to Our Additive Master Material (Page 125)

106 
Mastering Technical Art in Unreal Engine 
add in Parameters to help balance and adjust its effects, for example, a Multiply and a 
Vector Parameter to create a Color Tint. 
Let’s explore how to connect Particle Color to our Material M_VFXTrans. 
Utilizing Particle Color in Our Translucent Master Material 
1. In the Content Browser, navigate to the folder Content | Materials | 
Master. 
2. Double click on the Material M_VFXTrans to open the Material Editor. 
3. Open the Content Drawer and navigate to Content | Textures | 
VFX_Smoke. 
4. Drag and drop the Texture MagicCloud1 into the Material M_VFXTrans. 
5. Right click on the MagicCloud1 Texture Sample node and Convert it to a 
Parameter called ParticleTexture. 
6. Right click in the Material Editor Graph below the created Texture Sample, 
and search for ParticleColor. 
7. Create a Multiply node to the right of the ParticleTexture and Particle 
Color nodes. 
8. Connect the RGB output pins from the ParticleTexture and Particle Color 
nodes to the A and B inputs on the Multiply node. The idea is that the 
Particle Color will alter the color of the smoke. 
9. Connect the Output of the Multiply to the Base Color pin on the result 
node. 
10. Now create another Multiply node just underneath the frst one. 
11. Connect the R pin of the ParticleTexture node into the A input of the 
Multiply. 
12. Connect the A pin of the Particle Color node into the B input of the Multiply. 
13. Finally connect the Output pin of the Multiply node to our Opacity pin on 
the result node. 
14. Save the material. 
The four nodes shown in Figure 8.2 afford us the ability to manipulate a textures color 
and transparency through Unreal’s VFX system. We can increase the complexity of 
Materials like this by manipulating the UV’s of textures or by using Merged Maps to 
store different information in the RGBA channels of textures. 
Let’s now also add the Particle Color node to our Additive Master Material. 
Adding Particle Color to Our Additive Master Material 
1. In the Content Browser, navigate to the folder Content | Materials | 
Master. 
2. Double click on the Material M_VFXAdd to open the Material Editor. 
3. Open the Content Drawer and navigate to Content | Textures | EnergyOrb. 
4. Drag and drop the Texture Particle1 into the Material M_VFXAdd.

---

### Setting up Texture Parameters (Page 67)

48 
Mastering Technical Art in Unreal Engine 
Now that you have an idea of how material instances work, and how we can create 
parameters, we can modify the coin material we created in Chapter 4 to use param­
eters, making it possible to use the other coin textures in the Textures folder. 
Setting up Texture Parameters 
Texture Parameters enable the option for the end user of a material instance to swap 
out a selected texture in a material for a new texture suitable for their particular use 
case. This means that we can apply the same material base, via the use of material 
instances to objects with different UV layouts (thus requiring different textures) or 
simply replace the textures with a texture set with different colors or a different pat­
tern included. To do this, we need to change our Texture Sample nodes into Texture 
Parameters. 
1. Open the M_Coins material that we created in Chapter 4. 
2. Right click the Texture Sample connected to the Base Color pin and click 
Convert to Parameter. 
3. Set the parameter name as Base Color Texture. 
4. Repeat this process for each of the other Texture Sample nodes, naming 
them ORM Texture and Normal Map Texture. 
5. Click Apply and Save the material. 
With the texture parameters now set up, we can check how they appear in a material 
instance. 
1. Navigate to the Materials folder in the Content Browser where you saved 
the M_Coins material asset. 
2. Right click the M_Coins asset and select Create Material Instance. 
3. This should have created a new asset called M_Coins_Inst, rename it 
MI_Coins. 
The resulting asset should look very similar to the M_Coins asset however while the 
thumbnail preview of the MI_Coins asset will look the same, there are a few differ­
ences within the rest of the asset icon. Note that the green line underneath the thumb­
nail is now slightly darker and that the asset type is shown as Material Instance 
instead of Material on the M_Coins asset. 
With the asset created we can now take a look at how the parameters look within a 
material instance. Double click the MI_Coins asset and take a look, you should see the 
three texture parameters listed under a Global Texture Parameter Values section of 
the Parameter Groups rollout in the Details panel. This is typically on the right side 
of the window with a large viewport with a material ball taking up most of the window. 
We have included textures for different color versions of the coin which we can use 
to test the material instance out. 
When we create material instances, typically we would name them to make clear 
what the material is to be used for, for this example, we just changed the prefx from M

---

### Building the Material (Page 106)

87 
Mesh Painting and Materials 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
For the example in this chapter, we are going to blend the tiling foor material with 
a dirty coal material, frst adding the coal dirt into the grout between the foor tiles 
and, on stronger sections, piling it on top of the tiles. In order to do this we are going 
to use the Vertex Color to control a height based blend using a HeightLerp node. An 
alternative approach to blending two materials would be to just use a Lerp node for 
this similar to how we have controlled the Roughness and Metallic elements, but the 
HeightLerp node allows us to use a Height Map to get the effect of the dirt building 
up in between the tiles. The HeightLerp node uses two material (or color) inputs and 
three foat values that can be driven by a numerical value, or the output of a single 
channel from a texture, or in our case, the Vertex Color of the mesh. 
Now we’ve explored the nodes, let’s look at how we build those into a material. 
Building the Material 
For this example, we are going to build upon the M_TilingMaster from Chapter 6, 
adding the ability to blend a second set of textures into our material based on the green 
channel of an object’s vertex colors. 
The frst thing we need to do is duplicate the tiling master material and make a few 
changes to reduce the complexity of the material. To do this we are going to remove 
the Detail Normal section of the material and swap the default textures we previously 
used to the ones for the tiling foor. 
1. Navigate to Content | Materials | Master. 
2. Right click the M_TilingMaster and select Duplicate. 
3. Name the new material M_VertexPaintMaster. 
4. Click Save All to ensure the new material has been saved. 
5. Double click the M_VertexPaintMaster material to open it in the Material 
Editor. 
6. Select all of the nodes in the Normal Map and Detail Normals comment 
box EXCEPT for the Normal Map Texture and delete them. 
7. For now, reconnect the RGB pin from the Normal Map Texture to the 
Normal pin on the Material Output node. You can add a reroute node to tidy 
this up if you like. 
8. Rename the Normal Map and Detail Normals comment box to Normal 
Map. 
9. Swap all of the texture defaults on each of the Texture Parameter nodes 
(Base Color Texture, ORM Texture, Normal Map Texture) for textures 
form the Content | Textures | StoneFloor directory. 
Now we have a simplifed version of the material we can look at adding the Vertex 
Color based blending. We are going to start by adding in all of the additional textures 
we need to use. 
1. Select the three existing Texture Parameter nodes (Base Color Texture, 
ORM Texture, Normal Map Texture) and duplicate them with CTRL + D. 
2. Move the new nodes somewhere tidy so you can work on them.

---

### Render (Page 140)

121 
Introduction to Niagara and VFX in Unreal Engine 
Emitter Summary 
The Emitter Summary is a user created collection of the most important/frequently 
used properties of a Niagara Emitter. You may wish to use them when your Emitters 
become very complex to provide one menu option instead of diving into multiple 
property menus. It’s not vital that you use the Emitter Summary, however, you may 
fnd them helpful when revisiting older work or when sharing complex projects with 
team members. 
Emitter Spawn 
The Emitter Spawn group defnes what happens to our Particles when they are frst 
generated on the CPU. It only runs once and should be used to initialize System 
Defaults, the nodes are executed from top to bottom. You’ll fnd in many example 
templates and simple effects that this Stage is often empty. 
Emitter Update 
Emitter Update allows us to confgure how particles are created. For example, we can 
confgure particles to Spawn Instantly or at a Rate over time. There is also the option 
to Confgure the Emitter State. This provides us with the ability to set our Particles 
Life Cycle Mode. Our particle’s Life Cycle sets up whether an Effect loops, runs once 
or a set number of times. It’s possible for the Life Cycle setting to be confgured by 
the Niagara System; this can be useful if you want a number of Emitters to all behave 
in a similar way. 
Particle Spawn 
This group is called per Particle once they are created. During this stage we set 
parameters of our Particles such as Size, Color, Location and Velocity. Most of these 
parameters can be found in the Initialize Particle node. It’s likely that you will spend 
a fair bit of time at this stage; it is one of the most defning sections of an Emitter. 
Particle Update 
Particle Update controls what happens during a Particle’s Lifetime and is called every 
frame per particle. This stage handles a lot of the animation and behavior of our 
Particle Effects. For example, we may wish to scale a Particle over its life, alter its 
color or add complex physics to it. This stage relies on good foundations and param­
eters from the Particle Spawn, be careful not to rush through to the Particle Update 
stage as it’s quite easy to over complicate effects unnecessarily. 
Render 
The Render stage controls the visual appearance of a Nigara Emitter. We have several 
types of Particles we can render with the most common ones being Sprites, Meshes, 
Ribbons and Lights.

---

### Material Math (Page 68)

49 
Material Instances 
for material to MI for material instance, now we are going to set the material instance 
up with a different texture, so we should frst rename it before doing anything else. 
1. Select the MI_Coins asset and rename it MI_Coin_Silver. 
2. Open the MI_Coin_Silver asset. 
3. Turn ON the check box next to Base Color Texture. 
4. Change the texture to Coin_Silver_BaseColor. 
5. Repeat steps 3 and 4 for the Normal Map Texture and ORM Texture 
selecting the Coin_Silver_Normal and Coin_Silver_ORM respectively. 
You may not see much of a difference in the normal map (they are fundamentally 
the same texture) but you should see the preview material change signifcantly when 
swapping the ORM texture, this is because the values in the Roughness and Metallic 
channels of the texture are different from those in the textures for the gold coin. 
The MI_Coin_Silver material instance can now be used in the scene. Try applying 
it to one of the coins on the desk… 
We’ve also included textures for a copper coin, test your understanding and cre­
ate a material instance for the copper coin, using the copper coin textures. If you are 
unsure, follow the last two sets of instructions but change the names and selected 
textures. When complete, add it to one of the coins on the desk to see the different 
materials you’ve created. 
With these set up, tested and used in the scene we can now move on to more 
complex elements of the material, but before we do, let’s go and modify the group­
ings for the textures so they appear in appropriately named groups in the material 
instance editor. 
1. Open the M_Coins material. 
2. Click on the Base Color Texture node and, in the Details panel, click in the 
Group dropdown and type Base Color to create a new group. 
3. Repeat this for the ORM Texture node, creating a Roughness and Metallic 
group. 
4. Repeat again for the Normal Map Texture node, creating a Normals group. 
If you now check back in the material instance editor by opening either of the mate­
rial instances we’ve created (silver and copper), you should now see each texture in 
its own group. 
Material Math 
One of the key strengths of materials in Unreal Engine is the ability to perform 
math operations within the materials themselves. These operations are controlled by 
values in the graph which, often, we expose to the end user in a material instance. 
These mathematical operations get applied to each pixel of a texture on a model, 
unless masking is used, but we won’t over complicate matters with masks at this 
stage.

---

### Texture Formats and Compression (Page 43)

24 
Mastering Technical Art in Unreal Engine 
 
 
 
 
 
 
instructions in the material. Depending on the material and the usage of the 
mask, some grayscale textures may only contain either white or black pixels, 
these are referred to as Binary Masks. An example of using such a Binary 
Mask could be in a leaf material, where the model is a rectangular plane and 
the section of polygons which needs to be not visible, would be black on the 
mask whereas the leaf area would appear white. 
• Merged Map Textures – This type of texture has multiple different names, 
you may also fnd them referred to as mix maps or combined mask textures, 
with artists and studios using different names and labels, but all of these 
are used in the same way, to provide multiple images (or maps) for use in 
the material contained within a single texture fle, saving precious memory. 
These textures are often very odd to look at when viewing all three chan­
nels (RGB), in order to understand what the texture is bringing to the mate­
rial, we need to view the different channels as grayscale textures. These are 
typically used to replace the use of three separate grayscale textures used 
as inputs into the roughness, metallic, or ambient occlusion or may contain 
three binary masks to provide additional control to the material. Often, the 
naming convention with merge maps will depend on what textures are being 
saved in them. 
• Normal Map Textures – Normal maps are used in games to add extra light­
ing detail to materials, often to give the sense that we are viewing a higher 
polygon model than we actually are. The texture itself stores the direction 
perpendicular to the surface for each pixel. The directional data is stored in 
the RGB data of the texture with each channel corresponding to the world 
axes XYZ. It is important to remember that normal maps do not change the 
physical geometry of the model they are applied to, just how light interacts 
with the surface. Typically, normal maps are either generated from grayscale 
textures called height maps or baked from a high polygon model in a Digital 
Content Creation (DCC) tool such as 3D modeling software like 3DS Max, 
Maya, or Blender or texture generation software like Substance Painter or 
Substance Designer. 
• HDR Textures – High Dynamic Range (HDR) textures are a special type of 
texture with a higher bit depth than normal texture. HDR fles can be saved 
with up to 32 bits per channel and aren’t restricted by the typical, limited 
number of values. The values for each channel are also stored as foating‑
point numbers (foats) instead of integers, allowing for values to exceed the 
normal 0–1 range in Unreal and it’s this characteristic which separates HDR 
textures from normal textures. File formats for HDR textures are typically 
either the RGBE format (.hdr) or OpenEXR (.exr), both of which can be 
imported into Unreal Engine. In Unreal, we typically use HDR textures for 
lighting of scenes and backdrops when p

---

### An Introduction to Master Materials (Page 77)

6 
Master Materials 
In Chapter 5, we built the example material for the coins to be usable with material 
instances by building in well labeled and sorted parameters. These parameters are the 
building blocks of the core ideology of Master Materials, in this chapter, we are going 
to be exploring that further, you will learn about: 
• Additional techniques of how we design materials for others. 
• Optimizing material usage by maximizing the reusability of material with 
instances. 
• Working with tiling materials. 
At the end of the chapter, you’ll be all set up to create all of the material instances 
needed to fully texture the Wizard’s Desk environment. 
An Introduction to Master Materials 
Master materials allow us to create a single‑parent material, which can be used for 
lots of different materials in a scene. Master Materials are often very powerful and 
fexible materials with sections of their graph controlled with Boolean variables to 
be able to turn different sections on and off, providing control and usability but also 
effciency at runtime. 
When working on large projects, Master Materials are an invaluable resource to 
ensure a consistent art style between all materials, with materials for most objects 
having the same controls and functionality, and using the same inputs so assets can be 
produced in DCC packages, exported with their textures and new material instances 
can then create with ease, without the need to create new material graphs each time. 
Typically, when working with Master Materials, we will create a Master Material 
for each of the different Blend Modes in our project. We are going to be creating 
Master Materials for Glass (Translucent), Subsurface and Tiling Materials as well as 
re‑working the coin material as an Opaque, Base Master Material. 
Apart from subsurface, we could build all of the possible features of these into one 
single master material, opting to use a translucent blend mode and setting the opacity 
to 1 when wanting to create an opaque material, so why don’t we? Well, this approach 
would mean that every material we make is calculating translucency, even if the material 
is opaque, wasting a lot of memory and render time. It’s important as a Technical Artist, 
to identify not only when things are good ideas and will improve things but where an idea 
will have a negative effect on the product, in this case, using a single master material for 
all those options would be a bad idea and cause a signifcant waste of precious resources. 
DOI: 10.1201/9781032663852‑6 
58

---

### Particle Color (Page 124)

105 
Introductory Materials for VFX 
Shading Models 
Shading Models to help us create Materials that react correctly with our scene’s lights, 
we again explored these in Chapter 3. The two most common shading models utilized 
in VFX Materials are: 
1. Unlit – This Shading Model is great for visual effects which emit light/glow. 
It is also the fastest Shading Model to render and as such benefcial to use 
when possible. 
2. Default Lit – This is the default Shading Model and affords you access to 
lots of Material inputs. It is more expensive to render but sometimes neces­
sary when you want your VFX system to react accurately to scene lighting. 
Now that we’ve explored the more commonly used Shading Models for VFX Materials, 
let’s apply these to our two VFX Master Materials. 
Setting the Shading Model on Our Translucent Master Material 
1. In the Content Browser, navigate to the folder Content | Materials | 
Master. 
2. Double click on the Material M_VFXTrans to open the Material Editor. 
3. Using the Details panel, search for the property Shading Model. 
4. Set the Shading Model to Default Lit. 
5. Click the Save Button in the Material Editor. 
Setting the Shading Model on Our Additive Master Material 
1. In the Content Browser, navigate to the folder Content | Materials | 
Master. 
2. Double click on the Material M_VFXAdd to open the Material Editor. 
3. Using the Details panel, search for the property Shading Model. 
4. Set the Shading Model to Unlit. 
5. Click the Save Button in the Material Editor. 
Particle Color 
The Material Editor has a special node called Particle Color. This node allows us to 
read in Particle RGB color data as well as Alpha values, inside of Unreals Material 
Editor over a Particles Lifespan. This allows us to create effects such as changing the 
color of a fame effect from blue to orange or the glow strength of electrical sparks. 
In order to utilize Particle Color, we have to connect the node’s outputs to our 
Material Graph. It’s commonplace for the outputs to be connected to Material chan­
nels such as Base Color, Emissive and Opacity. When using the node you can also

---

### Flames – Sub UV Emitter (Page 180)

161 
The Dawn of Fire 
7. Double click on our MI_Smoke Instance to open the Material Instance 
Editor. 
8. Tick the box next to the Parameter SubUVTexture, this will allow us 
to change the Texture. Click the down arrow next to where the current 
Textures name is, which will be Fire and set this to Smoke. Lastly press the 
Save Button. 
9. Move both MI_Fire and MI_Smoke to the Content | Materials | Instances 
folder. 
We’ve now prepared our Material Instances so we can move on to Niagara. It’s wise 
to separate out Material instances between Fire and Smoke due to color, shape and 
motion differences. Try to break up your VFX into different material assets to afford 
greater control of your VFX in Niagara. 
Flames 
Flames – Sub UV Emitter 
We are now going to use these materials in our Fire Particle Systems. For the rest of 
this chapter, we are going to build a Flame Emitter, Smoke Emitter, Flame Embers 
Emitter and a Flames Background Emitter. This series of Emitters will join together 
to form our overall Fire System. It’s important to break down the effect and build up 
the layers slowly. When deciding on how to separate layers in your own project look 
for distinctive movement, color, appearance and animation. It is however not a race to 
use as many Emitters as possible, make them all count and have a distinct role. 
Let’s get started with our Flames Emitter. 
1. In the Content Browser, navigate to the Content | VFX folder. 
2. Right click anywhere in the VFX Folder and create a FX \ Niagara Emitter 
asset. From the pop up menu choose to create a new Emitter and set the 
Template to be Fountain and Label the asset FlamesSubUV_Emitter. We 
are going to customize many properties about this Emitter, it doesn’t really 
matter which template you start from. 
3. Double click on the FlamesSubUV_Emitter asset to open up the Niagara 
Editor. 
4. Click on the Sprite Renderer Module, replace the Material using the drop‑
down arrow and look for our Instance MI_Fire. 
5. Next look for the Sub UV options. Enable the Parameter Sub UV Blending 
Enabled. Set the Sub UV Image Size to be X = 6 and Y = 6. These numbers 
relate to the numbers of rows and columns in the original Fire Flipbook tex­
ture. When creating your own systems, you will need to adapt this number 
to match the source texture. 
6. Next select the Spawn Rate Module and set the Spawn Rate Parameter to 
65.

---

### Lava Material (Page 234)

215 
The Fire Tornado 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
The pebble stone mesh has a low polycount of 192 triangles. The structure of the 
mesh is angular and chunky with a plain material. We can swap the Material with 
something more dynamic to take this very basic shape and make it into something 
much cooler. 
Lava Material 
The frst Material we are going to make is the Lava Material. This material is designed 
for one main function, to make our rocks look like awesome lava and add some vari­
ety to the mesh. We are going to add variety by blending between two similar sets of 
textures. We have provided a lava and a non‑lava texture set, our Niagara System will 
dynamically blend between the two, creating a mixture of hot and cold rocks. We are 
going to apply this effect to several stages of the Material Graph so it won’t just alter 
the Color but the Emissive, Normal and other textures to create a complete effect. 
This is but one way of adding some variety to the fnal Niagara System. In addition 
to blending materials we could also have several mesh emitters that spawn slightly 
different geometry. With this approach we could use random foats to add variety to 
spawning and speed to create variation. 
Let’s now build our awesome material! 
1. In the Content Browser, navigate to the folder Content | Materials | 
Master. 
2. Right click in the Master folder and select Material from the menu. 
3. Call the Material M_Lava. 
4. Double click to open the Material. 
5. Right click in the Material Graph and search for the Dynamic Parameter 
Node. 
6. Select the Dynamic Parameter Node and, in the Details panel, label Index 
0 as Emissive and Index 1 as Lava. 
7. Drag out of the Emissive Output of Dynamic Parameter and from the 
menu create a Named Reroute Node. Label this Node EmissiveParam. 
8. Drag out of the Lava Output of Dynamic Parameter and from the menu 
create a Named Reroute Node. Label this Node LavaParam. 
9. You can review the structure so far against Figure 15.1, the two reroute 
nodes shall help us keep the Material Graph clean. They will allow us to 
place nodes independent of connection lines whenever we want to call the 
nodes. It’s great to use these nodes when you have a value that’s needed fre­
quently in several places. 
10. Next create two Texture Sample Nodes by holding T and left clicking in the 
Material Graph, you can convert them to Parameters if you’d like to make 
instances of this Material later. But for this tutorial it’s not required. 
11. Set the Texture property of the frst Texture Sample to Textures | VFX_ 
LavaRock | NonLava_BaseColor and Set the Texture property of the sec­
ond Texture Sample to Textures | VFX_LavaRock | Lava_BaseColor. 
12. Now create a Linear Interpolate Node by holding L and left clicking in the 
Material Graph.

---

### Tinting VFX Materials with Scalar and Vector Parameters (Page 130)

111 
Introductory Materials for VFX 
This panning approach can be layered with tiled texture coordinates fed into the 
Panner node. Try to duplicate the Panner section of the graph and experiment with 
different values fed into the ParticleTexture UV input. You may also observe a 
more complex version of this material in the following folder: Content | Completed | 
Materials | Master | EnergyOrb_Master_MAT. 
Tinting VFX Materials with Scalar and Vector Parameters 
The following exercise can be applied to both of our VFX Materials; however, we’ll 
continue with the additive Master. The instructions will provide you with color and 
opacity overrides at the Material level. The goal is that with a couple of nodes you can 
tweak an entire Niagara Effect’s look from a Material Instance if you wish to. 
Let’s begin: 
1. In the Content Browser, navigate to the folder Content | Materials | 
Master. 
2. Double click on the Material M_VFXAdd to open the Material Editor. 
3. Select all of the Nodes inside the Material and move them to the left to make 
some space between our instruction nodes and the output node. 
4. Above the ParticleTexture node, hold V and click in the Material Graph to 
Create a Vector Parameter node. Call this ColorTint. 
5. Select the ColorTint Node and use the Detail Panel to set its Default Value 
to White (R = 1, G = 1, and B = 1). 
6. Now hold M and click in the Material Graph to place a Multiply Node. 
7. Connect the RGBA output (white pin) of the ColorTint node into the A 
input of the new Multiply Node. 
8. Connect the Multiply output that is connected to our ParticleTexture node 
into the B input of the new Multiply Node. 
9. Connect the new Multiply node’s output pin to the Emissive Color input pin 
on the material output node. 
10. Create another new Multiply below, and connect its output into the Opacity 
input pin of the material output node. 
11. Connect the output of the Multiply node which is connected to the Particle 
Color node’s A pin to the recently created Multiply node’s A input. 
12. Next Hold S and left click in the Material Graph. This will create a Scalar 
Parameter, label this node OpacityStrength. 
13. Select the Opacity Strength node and using the Details panel set the Default 
Value of Opacity Strength to 1. 
14. Connect the output of Opacity Strength to the B input of our recently con­
nected Multiply Node. 
The completed Material can be seen in Figure 8.5 which shows the additive material 
master with four nodes added to provide controls for color tinting and opacity. Simple 
tweaks like this allow us to easily control the look of a Material, sometimes we need 
these overrides to make very quick adjustments.

---

### The Energy Orb Materials (Page 150)

10 
Creating the Energy Orb 
Introduction 
In this chapter, we are going to build the Energy Orb System, you’ll learn about: 
• Creating Materials with UV Distortion Effects. 
• Combining multiple Niagara Emitters in Niagara System Assets. 
• Managing Different Spawn Location Types. 
• Manipulating Velocities through Particle Update. 
The Energy Orb Materials 
To begin creating our Energy Orb, we need to make a new VFX Material, this is 
because we’d like a more chaotic energy and distortion in our Material. Fortunately, 
we can still leverage much of our existing M_VFXTrans_SmoothStep Material. 
During this next example we’ll make use of nodes such as Panners and Rotators to 
animate texture coordinates. We will then feed this animation into our Materials UV 
inputs to create a chaotic energy effect. 
Distorting textures is a big part of VFX Materials. The use of noise textures, tiling 
and animation is a great way to make an effect look more complicated than it really is. 
Try to keep a store of useful grayscale imagery for your VFX projects. You’ll be sure 
to fnd time for random noises to make effects look more powerful and stunning. Let’s 
now get started and build our Material! 
1. To get started navigate to Content | Materials | Master and select 
M_VFXTrans_SmoothStep. 
2. Right click on the asset in the Content Browser and click Duplicate from 
the popup menu. Label the duplicated Material M_VFXTrans_EnergyOrb. 
3. Double click on the new M_VFXTrans_EnergyOrb Material to open it in 
the Material Editor. 
4. Locate the ParticleTexture node, set the ParticleTexture Parameter to 
Particle1 by clicking the MagicCloud text and using the search box. You 
can set this Parameter using other methods if you prefer to fnd the Texture 
in the Content Browser instead. 
DOI: 10.1201/9781032663852‑10 
131

---

### Water Foam Material (Page 226)

207 
The Waterfall 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
Waterfall Foam Effect 
Water Foam Material 
In this next section we are going to build a Material that will power our Water Foam 
Particle Effect. This Material will use several of the effects we’ve used in previous 
chapters to create a foam pattern which we will animate in Niagara via the use of 
Particle Color and Dynamic Parameters. 
1. In the Content Browser, navigate to the folder Content | Materials | 
Master. 
2. Right click in the Master folder and select Material from the menu. 
3. Call the Material M_WaterFoam. 
4. Double click to open the Material. 
5. Navigate to the Details panel. 
6. Locate the Blend Mode Parameter, select Additive from the down menu. 
7. Set the Shading Model to Unlit. 
8. Create two Texture Sample Nodes in the Material Graph by Holding T 
and left clicking. Set the Texture Parameter to be WaterfallStream1_ 
BaseColor on both Texture Sample Nodes. 
9. To the left of the Texture Sample Nodes create two Texture Coordinate 
Nodes by right clicking in the Material Graph and searching for Texture 
Coordinate. On the upper Texture Coordinate Node set the U and V tiling 
to 2.5 and on the lower Texture Coordinate Node set the U and V Tiling to 
0.75. The idea here is to have one water texture that repeats a few times and 
one that is at a very large scale. 
10. Above the Texture Samples place a Particle Color Node by right clicking 
in the Material Graph and searching for Particle Color from the popup 
menu. 
11. Create two Multiply Nodes to the right of the Texture Samples, on the frst 
Multiply Node connect the R output of the Particle Color Node into the 
A input of the frst Multiply. Connect the R output of the upper Texture 
Sample into the B input of the frst Multiply node. 
12. On the second Multiply Node connect the G output of the Particle Color 
Node into the A input of the second Multiply node. Connect the R output of 
the upper Texture Sample into the B input of the second Multiply node. 
13. Create a new Multiply Node and set the A value to be 0.5 and connect the 
upper output of the frst Multiply node into value B. This will darken the 
repeating water texture. We do this as combining textures can lead to really 
bright values very easily. 
14. Next create an Add Node and connect the output of the upper Multiply Node 
into the A Input of the Add Node and the output of the second Multiply 
Node into the B input of the Add Node. An example of what we’ve done so 
far can be seen in Figure 14.10.

---

### Base Color Texture (Page 58)

39 
Creating Your First Material 
will help you create the look of a Material. We will explore many of these inputs over 
the coming chapter, however in this frst example we will only utilize Base Color, 
Roughness and Metallic. So, what do these three input pins represent? 
• Base Color is the overall color of a Material. It’s often represented by either 
a Texture or a Parametric R, G, B value. 
• Roughness controls a Materials scattering of refected light. With a value of 
0 being a mirror and a value of 1 a very rough/matte surface. 
• Metallic allows us to control whether a Material should look like a metal or 
not. A value of 0 could be more useful for plastic or stone and a value of 1 
could be used to represent material surfaces such as Gold or Silver. It is pos­
sible to use values in between to help replicate damaged or aged metals that 
might have dirt or dust on their surface. 
Adding Textures to the Material 
The frst thing we are going to do with our material is add some textures. The project 
fles include a lot of textures which we will apply to each of the different meshes. For 
the coin material we have three texture maps; a Base Color map, a merged Occlusion, 
Roughness, Metallic map labeled as ORM and a Normal map. 
To use textures in our materials, we need to use Texture Sample nodes. These nodes 
contain a reference (or link) to a texture asset from your Content Browser and a selec­
tion of settings, most of which we can leave alone for now. It is, however, worth being 
aware of the Sampler Type. 
The Sampler Type dropdown contains options which select how the selected tex­
ture is handled. The three we need to be aware of for this chapter are; Color, Normal 
and Linear Color. We will be using a Color sampler for our base Color texture, a 
Normal sampler for our Normal Map and a Linear Color sampler for our ORM tex­
ture. Typically, when you add a texture to your graph, Unreal will select the most 
suitable Sampler Type for your selected texture based on its Compression Group and 
Texture Group settings. 
Base Color Texture 
To begin with we are going to add the Base Color texture to the material. 
1. Click the Content Drawer button in the bottom left of the screen, this 
should open a popup just like the content browser, the difference with the 
drawer is it only stays open while you are interacting with it. Alternatively, 
you can press CTRL + Space to open it. 
2. Navigate to Textures | Coins | Gold and select the Coin_Gold_BaseColor 
texture asset so it is highlighted in the content drawer. 
3. Press and hold T and then click on the material graph, this will add the high­
lighted texture as a Texture Sample node to the graph. 
4. Drag from the RGB pin on the Texture Sample node and connect it to the 
Base Color pin on the result node (labeled M_Coins).

---

