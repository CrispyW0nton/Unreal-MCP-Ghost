# Book Knowledge: Technical Art & Optimization

> Extracted from 3 books. Total 15 relevant sections.

---

## Source: Mastering Technical Art in Unreal Engine (Greg Penninck)

### What Fields Are There Within Technical Art? (Page 24)

5 
What Is Technical Art 
So, now we know what you need to get into a team, let’s look at what that team 
might look like on the inside. 
How Does a Technical Artist Fit into a Development Team? 
As we have already mentioned, the Technical Art discipline acts as a bridge between 
programming and art. With that in mind, you are probably wondering what a team 
structure might look like with a technical artist in it? This will often depend on the 
company, as not all studios operate in the same way with Technical Art sitting more 
closely with code or art, so, let’s explore a couple of example studio setups. 
Figure 1.1 shows two possible placements for a Technical Art team within a smaller 
studio/development team, being managed by the Art Manager, therefore sitting along­
side art a bit more closely, or being led by the technical manager, resulting in the team 
sitting more closely with programming. In these instances, the expected skills may 
also be biased toward the team they are sitting within. Regardless of where the team 
sits, a technical artist will be expected to support multiple different teams including 
animation, art and design, so they could be responsible for many aspects of develop­
ment such as rigging, VFX, materials and general pipeline duties. 
Figure 1.2 shows a larger studio with a dedicated team. In larger studios, there 
might be multiple Technical Art areas. In these studios, the technical artists may align 
with a more focused feld, we will explore those next. 
Before we move on, however, it’s important to realize that while Figure 1.2 might 
visually suggest that Technical Art is a bigger department than the other areas, the 
number of staff in each of the roles within the Technical Art team will be much lower 
than, for example, each level of the design or programming team. We also haven’t split 
each of the other development areas down into their smaller parts, such as art is com­
monly split into environments, characters, vehicles or hard surfaces. 
What Fields Are There Within Technical Art? 
There are multiple disciplines that exist within Technical Art, you may be required to 
master some or all the following areas, and this is certainly not a defnitive list. 
• Technical Artist – In this more generalist role, you would be expected to 
support the art team with many technical challenges spreading across the 
development process. You would be an exceptional communicator who 
works closely with both programming and art to drive workfows and solu­
tions to technical challenges. 
• VFX Technical Artist – Technical artists in this more specifc role would 
work with the systems that integrate into the VFX Pipeline. You would have 
expert knowledge of materials, textures, lighting, physics and particle sys­
tems to support artists to create fantastic visuals with great performance. 
• Pipeline Technical Artist – A Pipeline Technical Art will work closely 
with the programming team to ensure the appropriate tools are avail

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

### Constants vs Parameters (Page 64)

5 
Material Instances 
In this chapter, we are going to explore Material Instances, a type of asset that allows 
us to create variations of materials without the need to create the whole graph again. 
You will learn about: 
• What material instances are and how we use them. 
• The difference between constants and parameters. 
• Material math and how we can apply it to our coin material. 
• Setting up color tints and controls for roughness values. 
• How to keep our material graphs tidy. 
We are going to continue building on top of the coin material we produced in Chapter 
4 to add features suitable for using with material instances. 
What Are Material Instances? 
When we build materials in Unreal Engine, we have the option to create Material 
Instances, this type of asset allows you to take an existing material and create versions 
that contain all of the same elements as the original material with the ability to change 
parameters such as colors, foats, Boolean values and textures which can be used as 
inputs into any of the material editor’s nodes. 
Material instances use inheritance, where a parent material passes all its properties 
(including all nodes, their inputs and settings) to the child material. In order to be able 
to change elements of the child material (or material instance) to make it look differ­
ent from the parent, the parent needs to feature parameters. We can convert any node 
which has an input into a parameter (such as a texture in the texture sample nodes we 
created earlier or vector/foat values in constant nodes we are going to create later 
in this chapter). Once converted the values become exposed in the material instance 
editor like those shown in Figure 5.1 where (from top to bottom) fve scalar (foat) 
parameters, a static switch (bool) parameter, three texture parameters and a vector 
(color) parameter are available for the user to modify, allowing them to adjust the 
visual result of the material instance. 
Constants vs Parameters 
When building materials in Unreal Engine, we need to decide what control we need 
to (or would beneft from) giving to artists in the team, what elements of the material 
DOI: 10.1201/9781032663852‑5 
45

---

### Constants vs Parameters (Page 65)

46 
Mastering Technical Art in Unreal Engine 
FIGURE 5.1 The Material Instance Editor showing a series of parameters which can be changed. 
we want to give them access to modify, and then build these into the material graph 
accordingly. 
Normal values in a material graph are called Constants, this is because, once 
created in the material, these values are set and remain the same unless you return to 
the graph to modify it. They are not changeable in material instances or at run time, 
and they don’t have a name assigned to them, they are, as the name suggests, constant. 
For a constant to become editable (either in a material instance or at run time), it 
must be converted into a parameter. Any value in a material graph, which can be set 
when we create materials, can be exposed to the user in a material instance. To do this, 
we right click on the node and choose Convert to Parameter. 
Figure 5.2 shows each of the main node types we will be using as both constants 
and parameters. Note how the parameter nodes (the nodes on the bottom row) don’t 
show their value in the top of the node, instead showing a name. This name is set when 
we convert the constant to a parameter but can be changed in the Details panel or by 
pressing F2 on the keyboard with the node selected. 
Also in the Details panel of a parameter are some properties that can help us to sort 
the parameters when they appear in the material instance editor. The three properties 
we are interested in are: 
• Group – This is a dropdown where we can select an existing group from or 
type into to create a new group; this allows us to separate the parameters into 
groups which display under different headings in the material instance edi­
tor. If this is left blank, the parameters will be sorted into type groups such 
as “Global Scalar Parameter Values”.

---

### Introduction to Technical Art (Page 20)

1 
What Is Technical Art 
In this chapter, we are going to talk about the role within the games industry which is 
Technical Art. You will learn about: 
• What Technical Art is. 
• What technical artists do. 
• What software a technical artist should learn. 
• What skills a technical artist should have. 
• How technical artists ft into a development team. 
• What felds there are within Technical Art. 
We will fnish the chapter with a short quiz to test your understanding of what we’ve 
discussed. 
Introduction to Technical Art 
In this chapter, we are going to explore Technical Art, but what is Technical Art you 
ask? Technical Art is an exciting feld of Games Development that revolves around 
three core concepts: 
1. Creating Solutions to Help Other Artists – Whether that’s a tool to help 
speed up a workfow or a template material to keep consistency, technical 
artists are frst and foremost focused on helping others work smart. 
2. Developing Systems and Art that Run Effectively at Run Time – You’ll 
know when something is hurting performance and guide others to produce 
content that looks great but doesn’t hurt gameplay. 
3. Researching and Creating Novel Solutions – Technical artists are always 
at the forefront of developing and looking for new techniques and systems to 
help create better content for others. 
If you enjoy building Game Art and want to take your understanding to the next 
level to support those around you, then Technical Art might be for you. The feld of 
Technical Art is very broad, the jobs and tasks you might need to complete require 
mastery of a large set of Game Engine Tools. As you progress through this book, and 
other books in the series, we will explore some of the most exciting areas. For now, 
let’s look at a couple of these areas at a high level. 
DOI: 10.1201/9781032663852‑1 
1

---

### Chapter 1 Quiz (Page 27)

8 
Mastering Technical Art in Unreal Engine 
deployment side of the pipeline working with a variety of different software 
and platforms. 
• Technical Animator – As the name suggests, this role is much more aligned 
with animation. You would likely focus on rig setup, animation pipelines, 
and animation systems setup. You would regularly work alongside the ani­
mators in your team, as well as gameplay programmers, to ensure that the 
animations function effectively and there are no blockers in the animation 
workfow. In larger studios, you might also work with hardware such as a 
motion capture stage to help support the integration of recorded motion cap­
ture performances including both body and facial performance capture. 
• Environmental Technical Artist – As games get bigger so do the technical 
challenges. Environmental Technical Art focuses on the creation of mas­
sive, stunning worlds. You are likely to work with procedural landscapes, 
world atmosphere, lighting, foliage tools and the population of vast detailed 
environments. 
• Virtual Reality/Virtual Production Technical Artist – Some platforms 
require very dedicated technical artists. In areas such as Virtual Reality 
(VR), Virtual Production (VP) or even Augmented Reality (AR), technical 
artists are likely to be working on a multitude of different hardware setups 
as well as different software. Your expertise could cover things like cameras, 
motion capture studios, in camera VFX pipelines, mobile platforms, VR 
headsets and more. 
Conclusion 
In this chapter, we’ve learned all about the role of a technical artist including what 
they do and how they might contribute to a game’s development. We’ve also covered 
some key considerations for creating portfolios as a technical artist applying for your 
frst role and we have taken a quick look at some of the other more niche roles within 
Technical Art. 
Chapter 1 Quiz 
Question 1: What Game Studio Departments do technical artists not work closely 
with? 
a. Art 
b. Programming/Engineering 
c. Marketing 
d. All of them, technical artists work alone 
Question 2: Which of the examples below are felds within Technical Art? (select 3) 
a. Environmental Technical Art 
b. Technical Art 
c. Character Art

---

### Building a Master Material for Tiling (Page 84)

65 
Master Materials 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
3. Create a new Multiply node by holding down M and clicking in the graph, to 
the right of the TexCoord[0] node. 
4. Create a new foat parameter by holding down 1 and clicking in the graph 
below the TexCoord[0] node and then convert it to a parameter (right click | 
Convert to Parameter) and call it Tiling. 
5. Set the Default Value of the Tiling parameter to 1.0 in the Details panel. 
6. In the Group parameter, type Tiling to put this control in a new group. 
7. Connect the three nodes together with the TexCoord[0] node connected to 
the A pin of the Multiply(0,1) node, and the Tiling output connected to the 
B pin as shown in Figure 6.3. 
8. Wrap the nodes in a comment box by pressing C, label the comment Tiling 
Controls and set the Comment Color to Black in the Details panel. 
9. Connect the output pin of the Multiply node in the Tiling Controls to the 
UVs pin on each of the three textures (Base Color Texture, ORM Texture 
and Normal Map Texture). 
10. Move the nodes so the connections are tidy. 
With the new tiling master built, let’s create a material instance which uses tiling and 
apply it to the foor in the scene. 
1. In the Content Browser, navigate to the folder Content | Materials | 
Master. 
2. Right click the M_TilingMaster and select Create Material Instance. 
3. Name the new material MI_StoneFloor. 
4. Drag the MI_StoneFloor Material Instance into the Instances folder and 
choose to Move Here from the popup. 
5. Double click the MI_StoneFloor asset to open it in the Material Instance 
Editor. 
6. Open the Content Drawer (CTRL + Space) and navigate to Content | 
Textures | StoneFloor. 
7. Use the textures to set the texture parameters of the material instance by 
frst clicking the checkbox next to a parameter and then dragging from the 
Content Drawer onto the texture icon. Set them as follows: 
a. Base Color Texture = StoneFloor_BaseColor 
b. Normal Map Texture = StoneFloor_Normal 
c. ORM Texture = StoneFloor_ORM 
The settings for the material instance should now look like those shown in Figure 6.4. 
Before we set the tiling, let’s apply the material to the foor mesh so we can see the 
effect of the tiling control in the world. 
1. In the viewport, click on the foor, it should be called StoneFloor_Mesh. 
2. In the Content Browser navigate to Content | Materials | Instances and 
select the MI_StoneFloor material.

---

## Source: Game Development with Unreal Engine 5 Volume 1 (Tiow Wee Tan)

### Complete the AutoBlend_Height_MAT Landscape Material (Page 140)

128
A group is set up to categorize related parameters within a material, facilitating 
easier navigation and adjustment.
Assigning a group name, such as “Ground” for ground-related texture parameters, 
consolidates these settings in the material instance, streamlining the interface for 
users and enhancing the efficiency of the material modification process.
This approach helps to organize our texture samplers when employing these 
materials outside the material editor.
 4. Connect UV Variation to AO_R: We will now parameterize the 
Texture Sampler that leads to AO_R.
 5. Set Parameter Name: The “Parameter Name” is set to “Ground_
AO_R” to identify the purpose of this parameter.
 6. Assign Group Name to AO_R: Similar to step 3, the “Group” field 
for the “Ground_AO_R” node is set to “Ground.”
 7. Connect UV Variation to Normal: We will now parameterize the 
Texture Sampler that leads to Normal.
 8. Set Parameter Name for Normal: The “Parameter Name” for the 
normal map is set to “Ground_Normal”.
 9. Assign Group Name to Normal: The “Ground_Normal” node’s 
“Group” field is set to “Ground,” keeping all related parameters 
organized under the same category.
Be sure to set the settings as follows: Shared Wrap for Sampler Source and 
Virtual Color for the Sampler Type.
These steps show the importance of proper organization and naming conventions 
in material setup, which can streamline the workflow and make it easier to manage 
complex materials.
Chapter 4 Revitalizing Visuals: Asset Import and Procedural Creation

---

## Source: Mastering Technical Art in Unreal Engine (Greg Penninck)

### Constants vs Parameters (Page 66)

47 
Material Instances 
FIGURE 5.2 Different constant nodes (top row) and their parameter equivalent (bottom row). 
FIGURE 5.3 Automatically grouped and ordered parameters (left) and manually grouped and 
ordered parameters (right). 
• Sort Priority – This integer value allows us to sort which order the param­
eters are listed in. The default value is 32. Parameters with higher values will 
appear lower in their grouped lists. 
• Desc – This can be used to provide a tooltip to the user when they hover 
over the parameter name in the material instance editor. Some parameters 
will be obvious as to what they do, others may beneft from a little bit of 
explanation to ensure anyone using your materials can understand what the 
parameters do. 
Making use of these can signifcantly improve the user experience of our materials. 
Figure 5.3 shows an automatically grouped and ordered list of parameters side by side 
with a manually confgured list of parameters. The right side shows the effect of using 
the Group and Sort Priority properties.

---

### Dirt Decals (Page 117)

98 
Mastering Technical Art in Unreal Engine 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
12. Connect the Roughness node to the Roughness pin on the Material Output 
Node. 
13. Press SPACE to open the Content Drawer and navigate to Content | 
Textures | Decals. 
14. Drag in the Splat texture. 
15. Right click the resulting Texture Sample node and choose Convert to 
Parameter. Name it Decal Texture. 
16. Add a Multiply node by holding down M and clicking on the graph. 
17. Connect the RGB pin of the Decal Texture to the A pin of the Multiply 
node. 
18. Connect the Opacity Strength node to the B pin of the Multiply node. 
19. Connect the output pin of the Multiply node to the Opacity pin on the 
Material Output Node. 
20. Set the Group of the various parameters to Decal, when setting this on the 
frst parameter, you will need to create it by typing it into the dropdown. 
21. Set the Sort Priority of the various parameters so they show in the fol­
lowing order; Decal Parameter, Decal Color, Specular, Roughness, Opacity 
Strength. 
The resulting material should look similar to the material shown in Figure 7.12. 
Because this is a simple material, there isn’t much need to add comment boxes. 
Dirt Decals 
With the material created, we can now create Material Instances to use three of the 
provided decal textures. 
1. Navigate to Content | Materials | Master. 
2. Right click the M_DecalMaster and select Create Material Instance. 
3. Name the new material MI_SplatDecal. 
4. Drag the MI_SplatDecal asset onto the Content | Materials | Instances 
folder and choose Move Here. 
• You could make the decals easier to fnd by adding a new folder in the 
Instances folder called Decals. 
5. Open the MI_SplatDecal material in the Material Instance Editor by dou­
ble clicking it. 
6. Set the following parameters: 
• Decal Color: Hex Linear (0B0705FF) 
• Specular: 0 
• Roughness: 1.0 
• Opacity Strength: 0.54 
With all of the parameters set, the decal is now ready to use in the scene.

---

### Spawning the Rock Particles (Page 243)

224 
Mastering Technical Art in Unreal Engine 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
Let’s get building! 
1. In the Content Browser, navigate to the Content | VFX folder. 
2. Right click anywhere in the VFX Folder and create a FX \ Niagara System 
asset. From the pop up menu choose to add Upward Mesh Burst to the asset, 
click Finish and then Label the asset FireTornado_System. 
3. Double click the FireTonardo_System to open the Niagara Editor. 
4. Disable or delete the Gravity Force Module. 
5. Disable or delete the Scale Color Module. 
6. Disable or delete the Scale Mesh Size Module. 
7. Disable or delete the Spawn Burst Instantaneous Module. 
8. Select the Emitter State Module and set the Loop Behavior Parameter to 
Infnite and set the Loop Duration to 8. 
9. Click the Orange + Button next to Emitter Update and select the Spawn 
Rate Module from the Popup Menu. 
10. Select the Spawn Rate Module and Set the Spawn Rate Parameter to 25. 
11. Set the Initialize Particle Module. Set the LifeTime Max Parameter to 
6. Change the Color Module Parameter to Direct Set using the dropdown 
menu arrow. Next Reset the Color Parameter to White using the Arrow 
Button. Set the Mesh Uniform Scale Min Parameter to 0.1 and the Mesh 
Uniform Scale Max Parameter to 0.42 and fnally reset the Mesh Renderer 
Array Visibility Mode Parameter to Unset. 
12. Select the Add Velocity Module. Set the Minimum Velocity Speed to 450 
and the Maximum Velocity Speed to 750. Increase the Cone Angle to 35. 
13. In the Particle Update Section, press the Green + Button and from the Menu 
search for the Vortex Force Module. 
14. Select the Vortex Force Module, set the Vortex Force Amount to 2500 and 
the Origin Pull Amount to 1500. 
15. In the Particle Update Section, press the Green + Button and from the Menu 
search for the Generate Location Event Module. 
16. Click the Emitter Properties at the top of the stack and enable Requires 
Persistent ID’s and Compile. 
17. In the Particle Update Section press the Green + Button and from the Menu 
search for the Dynamic Material Parameters Module. We’ll revisit this shortly. 
18. Now select the Mesh Renderer, delete Meshes Index [1] and change 
Index[0] mesh to be Meshes | Pebble_Stone_Mesh | Pebble_Stone_Mesh. 
Next change the Override Material Explicit Mat value to be M_Lava. 
19. Now select the Dynamic Material Parameters Module. Change the 
Emissive type to be a Random Float Range using the right dropdown arrow, 
set the Minimum Value to be 3 and the Maximum Value to be 15. 
20. Change the Lava Value to be a Multiply Float by Int, then change the 
Integer value to be a Random Range Int. 
21. Compile and Save the Niagara System. 
22. If you review against Figure 15.9, your Niagara System should look similar.

---

### Waterfall Splash Material (Page 220)

201 
The Waterfall 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
Waterfall Splash Material 
We are now going to build our Splash Material, this will be very similar to Materials 
that we created for our Fire and Smoke Effects earlier in the book. The material will 
represent water, foam and particles bouncing up from the river as the waterfall fall 
crashes downwards. The effect is often quite bright and white with a very thick water 
vapor appearance. 
We will begin by creating the basic requirements such as SUB UV control, blend 
modes and parameters. In a later section we’ll also explore adding refracting control 
to the effect to help distort the look, this will be optional and maybe something you’d 
like to add for a more realistic setting. Let’s begin: 
1. In the Content Browser, navigate to the folder Content | Materials | 
Master. 
2. Right click in the Master folder and select Material from the menu. 
3. Call the Material M_WaterfallSplashSubUV. 
4. Double click to open the Material. 
5. Navigate to the Details panel. 
6. Locate the Blend Mode Parameter, select Additive from the down menu. 
7. Set the Shading Model to Unlit. If you require better lighting you could 
also use the Translucent Blend Mode but it is more expensive. 
8. Make sure there’s a good bit of distance between the Material Result node 
and where your cursor is in the Material Graph. Then right click in the 
Material Editor Graph and place and search for a Particle Color Node. 
9. Just to the right of the Particle Color Node, hold M and left click to create 
a Multiply Node. Connect the RGB output of the Particle Color node into 
the A input of the Multiply Node. 
10. Right click just below the Particle Color node and search for a Texture 
Sample Parameter Sub UV Node. Set the Parameter Name to Texture Map. 
Set the Texture Map to our Splash Atlas texture. Connect the Red channel 
pin from the Texture Sample Parameter Sub UV Node to the B input of 
the Multiply node. 
11. Connect the output of the Multiply to the Emissive Color input on the 
Material Result Node. 
12. Place another Multiply node to the right of the Texture Sample Parameter 
Sub UV Node. Connect the Red channel pin from the Texture Sample 
Parameter Sub UV Node to the A input of the Multiply node. 
13. Hold S on the keyboard and left click below the Texture Sample Parameter 
Sub UV Node, this will create a Scalar Parameter Node. Rename the 
Parameter node OpacityStrength and set the Default Value to 0.84. 
Connect the output of OpacityStrength to the B input of the Multiply Node. 
14. With both of the Multiply inputs created, place another Multiply node and 
connect the output of the original Multiply Node into the B Input of the new 
Multiply Node. 
15. Connect the Alpha Output (A) of our Particle Color Node into the A input 
of the new Multiply Node.

---

## Source: Game Development with Unreal Engine 5 Volume 1 (Tiow Wee Tan)

### Complete the AutoBlend_Height_MAT Landscape Material (Page 148)

136
4-34
Further information about these parameters in the Global Scalar Parameters can 
be read as follows. The purpose of these parameters is to control various aspects of a 
material's appearance within our landscape in the level.
The numbers associated with each parameter, such as “Distance_Away”, “Falloff_
Lower_Half”, “Ground-Minimum”, “Middle_Mountain”, “Random Stripe Offset”, 
and “Top-Maximum”, represent specific values that have been set to define certain 
characteristics. For example:
• 
“Distance_Away” is to determine how texture or effects change with 
distance from the camera or a certain point.
• 
The “Falloff” parameter is to control the rate of change or transition 
between two states or areas, possibly affecting how textures blend or 
the intensity of an effect from one area to another.
• 
“Ground-Minimum” and “Top-Maximum” define the lower and 
upper bounds for the elevation of our landscape.
• 
“Middle_Mountain” specifies a midpoint value for elevation changes 
or another specific attribute related to our mountainous terrain.
• 
“Random Stripe Offset” is a value for introducing randomness to 
patterns or stripes, which might be part of a procedural texturing 
technique.
The specific negative or positive numbers indicate the magnitude or direction of 
the effect or value. The reason for these exact numbers would be based on the desired 
visual outcome or the technical requirements of the material within the game or scene. 
Designers adjust these values through experimentation and visual feedback to achieve 
the right look and performance.
The values assigned to the material parameters are based on the author’s artistic 
discretion and do not follow a specific formula. They have been fine-
tuned to the creator’s aesthetic preference, highlighting the subjective nature of 
visual design.
Chapter 4 Revitalizing Visuals: Asset Import and Procedural Creation

---

## Source: Mastering Technical Art in Unreal Engine (Greg Penninck)

### What Software Should I Learn? (Page 21)

2 
Mastering Technical Art in Unreal Engine 
What Do Technical Artists Do? 
Technical artists in game development act as a bridge between art and code, helping 
both the art team and the code team to deliver the requirements of the artistic vision 
while maintaining performant solutions that align with any technical restrictions. The 
main tasks a technical artist might undertake are: 
• Solve Problems – You will work with artists and programmers to fnd solu­
tions to game art problems, your work will cover a wide range of in‑game­
related issues such as rigs not working, materials not rendering properly, 
poor naming or tool usage. 
• Facilitate Artists – You will help others work smarter and faster. As a tech­
nical artist, you will often help remove blockers and enable artists to com­
plete their tasks effectively. 
• Devise Workfows – Part of facilitating others will be ensuring good work­
fows are followed. You will communicate across departments and create 
effective planning documentation and guides to help the work of others. 
This may mean populating wikis, creating technical documents or produc­
ing workfow videos. 
• Create Art – From time to time, you may be expected to create art assets. 
Technical artists often have a broad specialism and may be called up to help 
with Asset Generation during a project. 
• Develop Tools – Technical artists often create tools inside and outside of 
Game Engines to improve the effectiveness of Game Art Pipelines. 
Communication Is Key 
Another key part of the role, which is true for any game developer, is communica­
tion with other team members. For a technical artist, this is especially important as 
you will often be the interface between the art and technical teams, having a good 
understanding of both teams’ priorities and language. As part of that communication 
element, you will also be tasked with producing documentation to explain how things 
work (for the technical team to be able to review and refne) and how they should be 
used (for the art team to be able to use them on their assets), this side of communica­
tion, which includes visual and written elements is an important part of any technical 
artist’s week. 
What Software Should I Learn? 
A technical artist’s understanding of software packages and workfows is usually 
quite broad, even if their job role is quite specifc. While this book focuses on Unreal 
Engine, you can expect to work with many other pieces of software to help support 
your team. Some of the most common pieces of software used by technical artists 
are:

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### Creating the BP_EnemySpawner blueprint  (Page 296)

Spawning more enemies during gameplay 277
9. In the Pawn Class parameter, select BP_EnemyCharacter. In the Behavior Tree 
parameter, select BT_EnemyBehavior.
10. Drag a wire from the Location parameter and add a GetRandomPointIn 
NavigableRadius node. Set Radius to 10000.0. This node returns a random 
location based on the navigation mesh.
11. Drag a wire from the Origin parameter and add a GetActorLocation node:
Figure 10.27 – Setting the timer to spawn enemies
12. In the Event Graph of BP_EnemySpawner, drag a wire from the white execution 
pin of Event BeginPlay and add a Set Timer by Event node.
13. Check the Looping parameter. Drag a wire from the Time parameter and add a Get 
Spawn Time node.
14. Drag a wire from the Event parameter and add a custom event. Name it 
TryToSpawnEnemy.
15. Drag a wire from the white pin of TryToSpawnEnemy and add a Get All Actors Of 
Class node. In the Actor Class parameter, select BP_EnemyCharacter.
16. Drag a wire from the white output pin of Get All Actors Of Class and add a Branch 
node.
17. Drag a wire from the True pin of the Branch node and add the Spawn Enemy 
macro node.
18. Drag a wire from the Out Actors pin of Get All Actors Of Class and add a Length 
node. The return value of the Length node will be the number of enemies in the level.

---

