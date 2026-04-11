# Book Knowledge: Data Structures

> Extracted from 2 books. Total 15 relevant sections.

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### Set (Page 355)

336 Data Structures and Flow Control
The next screenshot shows some of the nodes of the set container. Here is a brief 
description of each node:
• ADD: Adds an element to a set.
• ADD ITEMS: Adds elements from an array to a set. The array must be of the same 
type as the set.
• CONTAINS: Returns true if the set contains the element.
• LENGTH: Returns the number of elements in a set:
Figure 13.20 – Nodes of the set container 
A set does not have a GET element node, so if you need to iterate through the elements of 
a set, then you can copy the elements of a set to an array. The next screenshot shows the 
TO ARRAY node and other nodes that are used to remove elements:
• TO ARRAY: Copies the elements of a set to an array. Note that copying a whole 
array of large objects can be a very costly operation.
• CLEAR: Removes all elements of a set.
• REMOVE: Removes an element of a set, or returns True if an element was 
removed and False if the element was not found.
• REMOVE ITEMS: Removes the elements specified in an array from a set:
Figure 13.21 – Nodes to remove items and convert a set to an array 
Some nodes perform operations with two sets and return a different set. These nodes are 
shown in the next screenshot:
• UNION: The resulting set contains all the elements from the two sets. Since the 
result is a set, all duplicates will be removed.
• DIFFERENCE: The resulting set contains the elements of the first set that are not in 
the second set.
• INTERSECTION: The resulting set contains only the elements that exist in 
both sets:

---

### Enumerations (Page 360)

Exploring other data structures 341
Exploring other data structures
There are data structures that are not created within a Blueprint class. They are independent 
auxiliary assets that can be used in a Blueprint. With these data structure assets, you are 
able to add your own data types to a project and can learn how to use tools that help 
you deal with a large volume of data in your project.
Let's learn how to create and use enumerations, structures, and data tables. 
Enumerations
An enumeration, also known as an enum, is a data type that contains a fixed set of named 
constants and can be used to define the type of a variable. The value of a variable whose 
type is an enumeration is restricted to the set of constants defined in the enumeration.
Follow these steps to create an enumeration:
1. Click the ADD button in the Content Browser, and in the Blueprints submenu, 
select Enumeration, as shown in the following screenshot:
Figure 13.32 – Creating an enumeration
2. There is a naming convention of starting the name of an enumeration with an 
uppercase E. Give the name EWeaponCategory to the created enumeration and 
double-click it to edit its values.

---

## Source: Mastering Technical Art in Unreal Engine (Greg Penninck)

### The Energy Storm Emitter (Page 156)

137 
Creating the Energy Orb 
4. Open the EnergyStorm_Emitter asset by double clicking it in the Content 
Browser. 
5. Select the Sprite Renderer Module and locate the Material parameter. 
Click where it says DefaultSpriteMaterial and using the Search options 
set the value to be M_VFXTrans_EnergyOrb. 
6. Next, select the Spawn Burst Instantaneous module and remove it by 
pressing the Delete Key. Click the Orange + button next to Emitter Update 
and select Spawn Rate. 
7. Select the SpawnRate module and set the Spawn Rate parameter to 3. 
8. Let’s now set some visual properties of our Particles, to do this select the 
InitializeParticle module and locate the LifeTime Parameter, click on the 
dropdown arrow to the right of where it says EmitterCurrentLoopDuration 
and set the value to Random Float in Range. 
9. Set the Minimum value to be 4 and the Maximum value to be 10. This will 
add a slight variation to the particles we spawn. 
10. Next, set the Color Mode to Direct Set and set the value to be R = 0.303821, 
G = 2.0, B = 3.0, and A = 1. 
11. Let’s now add a bit more size variation. Locate the Sprite Size Random 
parameter and set it to Random. Set the Uniform Sprite Size Min to 6 and 
Uniform Sprite Size Max to 16. 
12. Next, let’s add a bit of rotation, Click the Green + button next to Particle 
Update and search for SpriteRotationRate. 
13. Select the SpriteRotationRate module, click the dropdown arrow to the far 
right of the Rotation Rate value, and change the value to Random Float in 
Range. 
14. Set the Minimum value to be 0 and the Maximum Value to be 5. 
Let’s now preview the Effect so far in the Level: 
1. Select the Mesh MagicSphere_Mesh in the World Outliner. 
2. Ensure a Glass Material has been applied to Material Element 0, so that 
the Magic Sphere is Transparent. If you have not yet attempted the 
Glass Material, you can fnd a completed example in the folder Content | 
Completed | Materials | Instances | TubeGlass_Inst. 
3. Right click anywhere in the VFX Folder and create a FX\Niagara System 
asset. From the pop up menu select New System from selected emitters(s). 
4. Set the Asset Filtering to Parent Emitters. 
5. Left click on the EnergyStorm_Emitter before clicking the Green + button. 
We can then click Finish to create the System Asset. If you fnd this overly 
complex, you can always create an Empty System asset and drag and drop 
the Emitters into the System Asset when it’s open in the Niagara Editor. 
6. Label the Niagara System Asset as EnergyOrb_System. 
7. Ensure both Niagara System Asset and Niagara Emitters are all saved, you 
can do this in either the Content Browser, or Niagara Editor if you have the 
assets open.

---

### Waterfall Splash System (Page 222)

203 
The Waterfall 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
5. Disable or delete the Add Velocity Module. 
6. Disable or delete the Gravity Force Module. 
7. Disable or delete the Drag Module. 
8. Disable or delete the Scale Color Module. 
9. Select the Spawn Rate Module and set the Spawn Rate Parameter to 5. 
10. Select the Initialize Particle Module. Set the Lifetime Min to 1 and set the 
Lifetime Max to 3.5. Change the Position Offset to Random Range Vector, 
set the Minimum offset to (X = 5, Y = −25, and Z = 0) and set the Maximum 
offset to (X = 5, Y = 25, and Z = 0). Set the Sprite Size Mode to Random 
Non‑Uniform. Sprite Size Min to X = 300 and Y = 250 and Sprite Size Max 
to X = 500 and Y = 350. Lastly set the Sprite Rotation Mode to Unset. 
11. Click the Green + Button next to the Particle Spawn stage and from the 
popup menu select the Add Velocity Module. Set the Velocity to be Linear 
and Random Range Vector. Set the Velocity Minimum to (X = −0.001, 
Y = −0.001, and Z = 0) and Set the Velocity Maximum to (X = 0.001, 
Y = 0.001, and Z = 5). 
12. Click the Green + Button next to the Particle Update stage and from the 
popup menu select the Sub UV Animation Module. Set the Sprite Renderer 
Parameter, to match the Sprite Renderer Module. 
13. Click the Green + Button next to the Particle Update stage and from the 
popup menu select the Scale Sprite Size Module. Set the Template to 
Linear Ramp Up. 
14. Then click the Green + Button next to the Particle Update Stage and add 
a Color Module. Using the Upper Gradient track, add 1 value using the list 
below and remove any existing points. 
a. Point 0, V = 0, R = 3, G = 3.35, and B = 4 
For the Lower Gradient track (Transparency) the default values are fne. 
15. Select the Sprite Renderer Module. Set the Material Parameter to be M_ 
WaterfallSplashSubUV. Next enable SubUVBlending Enable and set the 
Sub Image Size values as X = 4, and Y = 4. Set the Default Pivot in UV 
Space to be X = 0.5 and Y = 1. Change the Alignment Parameter to Velocity 
Aligned. 
16. Click the Save Button in the Niagara Editor. 
An example of the completed System can be seen in Figure 14.6. We’ve now created 
the Splash System which will help reinforce the fowing materials to add further vol­
ume to our waterfall. We now need to place several Niagara System assets to test the 
visual appearance of the effect. While placing the assets try to avoid overly straight 
lines, this can make the particles stand out in a negative way. 
Let’s now test the system in the level. 
1. To do so, Open the Content Browser and navigate to the Content | VFX 
folder. 
2. Drag and drop a copy of the WaterfallSplash_System into the level.

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### Map (Page 358)

Exploring different types of containers 339
The following screenshot shows some map nodes to add an element, remove an element, 
and remove all elements of a map:
• ADD: Adds a key-value pair to a map. If the key already exists in the map, then the 
value associated with the key will be overwritten.
• REMOVE: Removes a key-value pair from a map. It returns True if the key-value 
pair was removed. If the key was not found, then the node returns False.
• CLEAR: Removes all elements of a map:
Figure 13.27 – Map nodes to add and remove elements
The following nodes are used to get the length of a map, check whether a key exists, and 
get the value associated with a key in the map:
• LENGTH: Returns the number of elements in a map.
• CONTAINS: Receives a key as an input parameter and returns True if the map 
contains an element that uses that key.
• FIND: The FIND node is like the CONTAINS node, but it also returns the value 
associated with the key used in the search:
Figure 13.28 – Map nodes to get the length and search for a key
The following nodes are used to copy the keys and values of a map to arrays:
• KEYS: This copies all the keys of a map to an array.
• VALUES: This copies all the values of a map to an array:
Figure 13.29 – Map nodes to copy the keys and values to arrays

---

### Array (Page 347)

328 Data Structures and Flow Control
To get a value from an array, use the Get (a copy) node. This node has two input 
parameters, which are a reference to an array and the index of the element, as shown in 
the following screenshot. The Get (a copy) node creates a temporary copy of the value 
stored in the array; therefore, any changes to the value retrieved will not affect the value 
stored in the array:
Figure 13.4 – Getting a value from an array
To modify an element of an array, use the Set Array Elem node. The example in the 
following screenshot sets the Item value to 10 of the element with Index set to 2:
Figure 13.5 – Setting a value in an array element
Two nodes can be used to add elements to an array. The ADD node adds an element to 
the end of the array. The INSERT node adds an element at the index passed as an input 
parameter, and all the elements that used to be in this index onward will move to the next 
indexes. For example, if we insert an element at index 2, then the previous element that 
was at index 2 will be moved to index 3. The element that was at index 3 will be moved to 
index 4, and so on. The length of the array dynamically increases when using these nodes. 
Both nodes receive a reference as parameters to an array and a reference to the element 
that will be added to the array:
Figure 13.6 – Adding elements to an array

---

### Structures (Page 362)

Exploring other data structures 343
Figure 13.35 – Setting the value of an enumeration variable
For each enumeration type, there is a Switch on node that is used to change the execution 
flow based on the enumeration value, as shown in the following screenshot:
Figure 13.36 – Using the Switch on node on an enumeration
This is all we need to know about enumerations. The next data asset we will look at is 
the structure.
Structures
A structure, also known as a struct, is a composite data type that can group variables of 
different types into a single type. An element of a structure can be of a complex type, such 
as another structure, array, set, map, or object reference.

---

### The BP_Configurator Blueprint (Page 540)

The BP_Configurator Blueprint 521
Now, let's look at the functions:
Figure 20.11 – The BP_Configurator functions
This is what each function does: 
• initConfigVarSets: It gets the Variant Sets of the Level Variant Sets Actor and stores 
them in the ObjectVariantSets array, the EnviroVarSet variable, and the 
CameraVarSet variable. 
• resetAllVariants: Calls the resetVariant function for EnviroVarSet, 
CameraVarSet, and each element of the ObjectVariantSets array.
• resetVariant: Resets a Variant Set by activating the first element of the Variant Set.
• callVariantActorAction: Calls the Variant Switched On function for all 
Actors and components used by the current Variant that implements the 
BPI_RuntimeAction interface. This allows Actors to run script when the 
Variant is activated. 
• callVariantActorInit: Calls the Variant Initialize function for all 
Actors and components used by the current Variant that implements the 
BPI_RuntimeAction interface.
• activateVariant: Activates a Variant of a given Variant Set.
• initCamera: Initializes the camera.

---

### Index (Page 554)

Index 535
Components
adding, to Blueprint 17-19
constraints
applying, to player actions 180
Construction Script
about 54-58, 490
used, for procedural generation 490-492
containers, types
array 326-329
exploring 326
map 338-340
set 335-337
control inputs
customizing 134, 135
D
data pins 28
data structures
data table 347-350
enumeration (enum) 341, 342
exploring 341
structure (struct) 343-347
data table
about 347
creating 347-350
debug lines
about 376
parameter 376
delta time 119
destructions
triggering 148-151
Direct Blueprint Communication 70-76
Disable Input node 404
Do N node 355
Do Once node 354
E
Editor Utility Blueprint
about 505, 506
Actor Action Utility, creating 506-510
Editor Utility Widget 505
Enable Input node 404
encapsulation 44
End Game Event
modifying 299, 300
enemies
making destructible 272-275
making, to hear and 
investigate sound 263
spawning, during gameplay 275
enemy actor
setting up, to navigate 220
enemy actor navigation
AI assets, creating 229-231
behavior, creating 233
BP_EnemyCharacter Blueprint, 
setting up 231-233
importing, from Marketplace 220, 221
level, making traversable with 
NavMesh asset 227, 228
play area, expanding 221-227
setting up 220
enemy actor navigation behavior
Behavior Tree, running in AI 
Controller 241, 242
Blackboard keys, creating 234, 236
creating 233
current patrol point key, 
creating 237-239
modeling, with Behavior Tree 242-246
patrol point, overlapping 239-241

---

## Source: Mastering Technical Art in Unreal Engine (Greg Penninck)

### Magic Spell – Beam Emitter (Page 191)

172 
Mastering Technical Art in Unreal Engine 
Let’s get started! 
1. In the Content Browser, navigate to the Content | VFX folder. 
2. Right click anywhere in the VFX Folder and create a FX \ Niagara Emitter 
asset. From the pop up menu choose to create a new Emitter and set the 
Template to be Dynamic Beam and Label the asset MagicSpellBeam_Emitter. 
3. Double click the MagicSpellBeam_Emitter to open the Niagara Editor. 
4. Select the Emitter State Module. Set the Loop Behavior to 0.1, eventually 
we’ll set this behavior to be controlled by the fnal System asset. 
5. Select the Beam Emitter Setup Module, set the Absolute Beam End 
checkbox to TRUE. We’ll customize this asset in the System asset as well. 
For now though set the Beam End value to X = 500, Y = 0, and Z = 0. If we 
were building a Beam with a calculated target, the Beam End value is what 
we’d set in Blueprint, it’s often updated by Line Trace’s to simulate a weapon 
projectile hitting a target. 
6. Next, select the Initialize Module and set the Lifetime Value to 0.1. 
7. Let’s now change the color of our beam. Select the Color Module and set 
the RGB values to R = 1.3, G = 25, and B = 0.38. This will make our Beam 
glow a very bright green hue. 
8. Next, click the Green + Button next to the Particle Update Stage and add 
a Jitter Position Module. This will add a lot of noise to the beam. Set the 
Jitter Amount Parameter to 7.3. The frequency of the Jitter is dependent on 
the amount of particles created, in our effect, 100 particles are created in the 
Spawn Instantaneous Module. If we wanted to create a smoother looking 
beam we could either spawn fewer particles or add less Jitter. 
9. Now let’s create a pulsing effect that goes down the beam. To do this click 
the Green + Button next to the Particle Update Stage and add a Curl Noise 
Force Module. 
10. Select the Curl Noise Force Module. Change the Noise Strength parameter 
to use a Float from Curve Noise by using the dropdown arrow to the right. 
Setup the following four points on the graph as follows: 
a. Point 1, X = 0, and Y = 0 
b. Point 2, X = 0.1, and Y = 7500 
c. Point 2, X = 0.9, and Y = 7500 
d. Point 4, X = 1, and Y = 0 
11. Change the Curve Index Parameter to Ribbon Link Order using the drop‑
down arrow on the right. 
12. Set the Scale Curve Parameter to 5. 
13. Adjust the Noise Frequency Parameter to 5. 
14. Enable the Pan Noise Field Checkbox and see the X Value to 25. Our Beam 
will now look like it’s moving both vertically and horizontally. Lower values 
of 0–5 will show the movement through the noise feld more clearly while 
a higher value will add a bit more chaos. Many of these settings will need 
testing in your game levels to check appearance and look.

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### Optimizing your graphics settings (Page 330)

Optimizing your graphics settings 311
2. Hover over Engine Scalability Settings to see a pop-out display of the Quality 
settings that you can tweak, as seen in the following screenshot:
Figure 12.2 – Engine Scalability Settings elements
3. The buttons along the top of this menu, ranging from Low to Epic, serve as presets 
of the settings based on the broad level of performance versus quality that you want 
to target at runtime. Clicking on the Low button will set all the quality settings to 
the minimum, giving you the best possible performance, in exchange for the least 
visually attractive settings. Epic is the opposite end of the spectrum, raising all the 
engine quality settings to their maximum, at the expense of significant performance, 
depending on the assets you have chosen to use.
4. The Cinematic button will set all the quality settings to cinematic quality, which is 
used for rendering cinematics. This setting is not intended for use during gameplay 
or at runtime.
5. The Auto button will detect the hardware of the machine you are currently running 
the Editor on and adjust the graphics settings to a level that strikes a good balance 
between performance and a graphical quality that is suitable for your machine. 
If you are intending to target hardware that is roughly equivalent to the machine 
you are developing on, using the Auto setting can be a simple way to establish the 
graphics settings for your build.

---

## Source: Mastering Technical Art in Unreal Engine (Greg Penninck)

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

### Flames System (Page 186)

167 
The Dawn of Fire 
5. Change the Sub Image Size X to 8 and the Sub Image Size Y to 4. Ideally, 
we also want our Flip Book textures to be in the power of two to MIP prop­
erly, in this example the smoke is a rectangle. Keep an eye when sourcing 
your own Flip Books as they can come in all shapes and sizes. 
6. Select Emitter State Module and set the Loop Duration to 5. 
7. Select the Spawn Rate Module and set the Spawn Rate Parameter to 25. 
8. Next, click the Initialize Particle Module, lower the Lifetime Max to 5. 
9. Set the Color to R = 0.11, G = 0.11 and B = 0.11. This is a deep gray, the 
colors you see in the Niagara Editor Viewport will likely be a lot brighter 
for the Smoke Material. Be sure to revisit some of the Color properties after 
building the System Asset later. 
10. Set the Position Mode to Simulation Position. Add a position offset of X = 0, 
Y = 3 and Z = 25. This will move the whole smoke simulation upwards and a 
bit behind the Fire effect. 
11. Set the Uniform Sprite Size Min to 125 and Set the Uniform Sprite Size 
Max to 275. 
12. Select the Shape Location Module and set the Sphere Radius to 0.5. 
13. Next, select the Add Velocity Module, change the Velocity Mode to Linear. 
Change the Velocity type to a Random Range Vector using the dropdown 
arrow to the right. Set the Velocity Minimum to X =−5, Y =−5 and Z = 15. 
Set the Velocity Maximum to X = 5, Y = 5 and Z = 25. 
14. Select the Scale Sprite Size Module and change the template to Ease In. 
15. Select the Color Module, remove all of the fre colors on the upper track. 
Place a single Dark Gray on the Upper Track with a value of R = 0.08, 
G =0.08 and B = 0.14. This will create a very subtle blue tint to the smoke. 
16. Lastly select the Sub UV Animation Module. Set the End Frame Range 
Override to 0. 
A completed example of the Flames Smoke Emitter can be seen in Figure 12.8. 
We’ve now built our Emitters, feel free to adjust their properties and hone in the 
visuals as you wish. 
Flames System 
We now need to build the Niagara System asset so we can test the VFX in our level. 
1. In the Content Browser, navigate to the Content | VFX folder. 
2. Right click in the VFX Folder and create a Niagara System Asset. From 
the pop up menu, select New system from selected emitters(s). Then enable 
Parent Emitters to change the flter of what templates we can select. Ctrl 
click on the 4 Flames Emitters and press the Green + button and then click 
Finish. 
3. Label the created System Asset Flames_System. An example of the com­
pleted Niagara System Asset can be seen in Figure 12.9.

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### Array (Page 348)

Exploring different types of containers 329
You can get the number of elements in an array by using the LENGTH node. Since the 
index of an array starts at zero, then the index of the last element will be LENGTH – 1. 
Alternatively, you can use the LAST INDEX node, which returns the index of the last 
element of the array. The following screenshot shows these two nodes:
Figure 13.7 – Getting the length and last index of an array
Note
Be careful not to access an index in an array greater than the last index. It may 
give unexpected results and, in turn, cause crashes that may be difficult to track 
down later.
You can use the Random Array Item node to get a random element of the array. The IS 
EMPTY or IS NOT EMPTY nodes are used to check whether the array has elements:
Figure 13.8 – Nodes to get a random array element and to check whether the array has elements
The Make Array node is used to create an array from variables in the EventGraph. Click 
on Add pin + to add input pins. The example in the screenshot is from a Level Blueprint. 
There are four instances of PointLight in the level, and the Make Array node is used to 
create Point Lights Array: 
Figure 13.9 – Using the Make Array node

---

