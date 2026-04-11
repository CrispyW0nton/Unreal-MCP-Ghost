# Book Knowledge: Input System

> Extracted from 2 books. Total 15 relevant sections.

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### The Set Input Mode nodes (Page 423)

404 Blueprints Tips
Enable Input and Disable Input
The Enable Input and Disable Input nodes are functions used to define whether an actor 
should respond to inputs events such as from a keyboard, mouse, or gamepad. The nodes 
need a reference to the Player Controller class in use.
A common use of these nodes is to allow an actor to only receive input events when the 
player is near the actor, as shown in the following screenshot:
Figure 15.35 – Example of Enable Input and Disable Input nodes
The Enable Input node is called when the player begins to overlap the Blueprint. When 
the player finishes overlapping the Blueprint, the Disable Input node is called.
The Set Input Mode nodes
There are three Set Input Mode nodes that are used to define whether the priority in 
handling user input events is with the UI or with the player input. These are the nodes:
• Set Input Mode Game Only: Only Player Controller receives input events.
• Set Input Mode UI Only: Only the UI receives input events.
• Set Input Mode Game and UI: The UI has priority in handling an input event, but 
if the UI does not handle it, then Player Controller receives the input event. For 
example, when the player overlaps a Blueprint representing a shop, a UI is displayed 
with options for the player to choose to use the mouse, but the player can still use 
the arrow keys to move away from the shop.

---

### Adding Animation States (Page 467)

448 Animation Blueprints
Adding Animation States
In this section, we will modify the Character Blueprint and Animation Blueprint that 
come in the Animation Starter Pack. We will add the following states to the State Machine:
• Prone
• ProneToStand
• StandToProne 
We will use the project created at the start of the chapter, which is using the Character 
from the Animation Starter Pack.
First, let's create the input mappings that we are going to use in our example. We will 
create two input actions: Crouch and Prone.
Note
The actions and states for the Crouch input action are already present in the 
Animation Starter Pack. To make Crouch work, we just need to add, in Project 
Settings, an action mapping named Crouch.
Follow these steps to create the input mappings:
1. Click the Settings button on the far right of the toolbar, and then select the Project 
Settings… option:
Figure 17.30 – Accessing Project Settings
2. On the left side of the window that appears, look for the Engine category and select 
the Input option.
3. Inside the Engine category, in the Input Settings menu, you will see two sections 
under the Bindings category called Action Mappings and Axis Mappings. Click on 
the > symbol in the Action Mappings section to show the existing mappings.
4. Click on the + sign next to Action Mappings twice to add two action mappings:

---

## Source: Mastering Technical Art in Unreal Engine (Greg Penninck)

### Animated Flowing Water Material (Page 217)

198 
Mastering Technical Art in Unreal Engine 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
1. Using the Content Browser Navigate to Content | Textures | VFX_ 
Waterfall, select and drag the Texture WaterMask into the M_ 
FlowingWater Material. Place the new Texture Sample slightly above our 
two Panner Node chains. This texture will be used to add extra brightness 
in the middle of Material and fade out the opacity near the edges. 
2. Place an Add Node by holding A and left clicking in the Material Graph. 
Connect the RGB output of the Texture Sample into the A input of the Add 
Node. Then connect the Multiply Output (from Panner chains) into the B 
input of the Add Node. Clicking the dropdown Preview on the Add node 
should now show the Panning water textures with the extra brightness added 
to the middle. 
3. Next we need to mask out the edges. To do this place a Multiply Node 
after the Add Node by holding M and left clicking in the Material Graph. 
Connect the output of the Add Node into the B input of the Multiply Node. 
Connect the RGB output of the WaterMask Texture Sample Node into 
the A input of the Multiply Node. If all’s gone well the edges of the texture 
should now be darker while the center section remains bright. 
4. We’ll now use this Node chain to create the color for our Material. To do 
this frst add a Saturate Node by right clicking in the Material Graph and 
searching for Saturate. Connect the Multiply Nodes output into the Saturate 
Node’s input. This will limit the Grayscale values to 0–1 which will help us 
ensure we don’t over infate our color values. 
5. Next hold L and left click in the Material Graph to create a Linear 
Interpolate Node. Connect the Saturate Node’s output into the B input 
of the Linear Interpolate Node. Set the Alpha Value to 0.5. Don’t worry 
about the A input, we will come back to that shortly. 
6. Hold M on the keyboard and left click to place a Multiply Node. Connect 
the output of the Linear Interpolate Node into the B input of the Multiply 
Node. Hold V on the keyboard and click to place a Vector Parameter Node. 
Label this Vector Parameter as Color Tint and set its Default Value to be 
White (R = 0.29, G = 0.37, and B = 0.88). 
7. Connect the RGB output of the Vector Parameter into the A input of the 
Multiply Node. Finally connect the output of the Multiply Node into the 
Emissive Color input on our Material Result. 
8. We now have to back track a bit to the Linear Interpolate Node. We need to 
create four nodes to create the logic that plugs into A. The idea here is that 
we will Blend a blue water texture with the animated panning mask. This 
will create a white volume of water in the middle with blue fner details near 
the outer sections. 
9. Place a Texture Coordinate Node by right clicking in the Material Graph 
and searching for Texture Coordinate. Place the node a bit to the left of the 
Linear Interpolate Node and leave a bit of sp

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### Customizing control inputs (Page 154)

Adding the running functionality 135
2. On the left side of the window that appears, look for the Engine category and select 
the Input option. 
3. Inside the Engine category, in the Input Settings menu, you will see two sections 
under the Bindings category called Action Mappings and Axis Mappings. Click on 
the > symbol on the left of each section to show the existing mappings. 
Action Mappings are keypress and mouse click Events that trigger player Actions. 
Axis Mappings map player movements and Events that have a range, such as the 
W key and S key both affecting the Move Forward Action, but on different ends of 
the range. Both our Sprint and Zoom functions are simple Actions that are either 
active or inactive, so we will add them as Action Mappings:
Figure 6.6 – Creating Action Mappings
4. Click on the + sign next to Action Mappings twice to add two new Action 
Mappings.
5. Name the first Action Sprint and select the Left Shift key from the drop-down 
menu to map that key to your Sprint Event. Name the second Action Zoom and 
map it to Right Mouse Button. 
The changes are saved when you close the window.

---

### Draining and regenerating stamina (Page 209)

190 Creating Constraints and Gameplay Objectives
9. Drag a wire from the Return Value pin of the VectorLengthSquared node and 
connect it to the top input pin of the Greater node.
10. Drag a wire from the bottom input pin of the AND node and add a Greater node.
11. Drag a wire from the top input pin of the Greater node and add a GET Player 
Stamina node.
12. Drag a wire from the True output pin of the Branch node and add a SET Player 
Stamina node. Connect the white output pin of the SET Player Stamina node to 
the Out pin of the Outputs node.
13. Drag a wire from the input pin of SET Player Stamina and add a Max (float) node. 
This node returns the highest value of the input parameters. We use this node to 
ensure that Player Stamina will never be less than 0.0.
14. Drag a wire from the top input pin of the Max (float) node and create a Subtract 
node.
15. Drag a wire from the top input pin of the Subtract node and add a GET Player 
Stamina node.
16. Drag a wire from the bottom input pin of the Subtract node and add a GET Sprint 
Cost node.
17. Drag a wire from the False output pin of the Branch node and add the Stop 
Sprinting macro node. Connect the white output pin of the Stop Sprinting node to 
the Out pin of the Outputs node.
Creating the ManageStaminaRecharge macro
The ManageStaminaRecharge macro recharges Player Stamina until it is full. 
Follow these steps to create the macro:
1. In the My Blueprint panel, click the + button in the MACROS category to create 
another macro. Change the name of the macro to ManageStaminaRecharge.
2. In the Details panel of the macro, create an input parameter named In of the Exec 
type and an output parameter named Out of the Exec type as shown in Figure 8.7.
3. On the tab created for the ManageStaminaRecharge macro, add the nodes seen in 
the following screenshot. If Player Stamina is full (nearly equal to 1.0), we clear 
the timer for Stamina Manager. If Player Stamina isn't full, we increment it.

---

### Draining and regenerating stamina (Page 211)

192 Creating Constraints and Gameplay Objectives
12. Drag a wire from the top input pin of the Min (float) node and create an Add node.
13. Drag a wire from the top input pin of the Add node and add a GET Player Stamina 
node.
14. Drag a wire from the bottom input pin of the Add node and add a GET Stamina 
Recharge Rate node.
Updating the InputAction Sprint event
We need to modify the InputAction Sprint event to use the new stamina system. 
Follow these steps: 
1. Look in the GRAPHS category of the My Blueprint panel and double-click on 
InputAction Sprint. The editor will move to the position in Event Graph where 
InputAction Sprint is already placed:
Figure 8.13 – Finding the InputAction Sprint event 
2. Delete the previous nodes that were connected to InputAction Sprint. We will add 
the nodes seen in the following screenshot. When the Shift key is pressed, the game 
checks whether there is enough stamina to begin sprinting, that is, whether the 
current PlayerStamina amount is greater than or equal to SprintCost. If the player 
has enough stamina to start sprinting, the Start Sprinting macro is called. When 
the Shift key is released, the Stop Sprinting macro is called.

---

### Draining and regenerating stamina (Page 212)

Constraining player actions 193
Figure 8.14 – The new version of the InputAction Sprint event
3. Drag a wire from the Pressed output pin of the InputAction Sprint node and add 
a Branch node.
4. Drag a wire from the Condition input pin of the Branch node and add an OR 
Boolean node.
5. Drag a wire from the top input pin of the OR node and add a Greater node. 
We cannot use the Greater Equal node because we need to use the Nearly Equal 
(float) node to verify that the two Float variables are equal. 
6. Drag a wire from the top input pin of the Greater node and add a GET Player 
Stamina node.
7. Drag a wire from the bottom input pin of the Greater node and add a GET Sprint 
Cost node.
8. Drag a wire from the bottom input pin of the OR node and add a Nearly Equal 
(float) node.
1. Drag a wire from the A input pin of the Nearly Equal (float) node and add a GET 
Player Stamina node.
2. Drag a wire from the B input pin of the Nearly Equal (float) node and add a GET 
Sprint Cost node.

---

### Triggering the pause menu (Page 325)

306 Game States and Applying the Finishing Touches
2. On the left side of the window that appears, look for the Engine category and select 
the Input option. Click on the + sign next to Action Mappings. Name the new 
action Pause and select the Enter key from the drop-down menu to map that key to 
the Pause Event:
Figure 11.28 – Creating an Action Mapping
3. In the Content Browser, access the Content > FirstPersonBP > 
Blueprints folder and double-click on the FirstPersonCharacter Blueprint.
4. Right-click on Event Graph, search for input action pause, and add the 
Pause Event node. Copy all the nodes from the LostGame Custom Event and paste 
them near the InputAction Pause node: 
Figure 11.29 – InputAction Pause Event actions
5. Connect the Pressed pin of the InputAction Pause node to the white input pin of 
the Set Game Paused node.
6. Change the Class parameter of the Create Widget node to Pause Menu.
7. Compile, save, and then click on Play to test.

---

## Source: Mastering Technical Art in Unreal Engine (Greg Penninck)

### Lava Material (Page 235)

216 
Mastering Technical Art in Unreal Engine 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
FIGURE 15.1 Dynamic parameter setup. 
13. Connect the frst Texture Sample into the A input of the Linear Interpolate 
Node and connect the second Texture Sample into the B input of the Linear 
Interpolate Node. 
14. Right click in the Material Graph and search for the LavaParam reroute node 
from the popup menu, Then connect the LavaParam Node to the Alpha 
input of the Linear Interpolate Node. Finally drag out from the Linear 
Interpolate Node and connect it into the Base Color Input of the Material 
Result Node. You can review this stage against Figure 15.2. 
The rest of the Lava Material will build on the above approach. The Roughness and 
Normals stages will duplicate the approach almost exactly, whereas our Emissive 
input needs a little more variety to allow us to toggle between a pure black (off emis­
sive) and a Lava Texture. Let’s build the rest of the material. 
1. Create Two Texture Sample Nodes like we did previously. Set the frst 
Texture Sample to Textures | VFX_LavaRock | NonLava_ORM and Set 
the second Texture Sample to Textures | VFX_LavaRock | Lava_ORM. 
2. Create a Linear Interpolate Node and Connect the Texture Sample Nodes 
to the Linear Interpolate Inputs. 
3. Create a LavaParam Node and connect it to the Alpha input on the Linear 
Interpolate node. 
4. Then Connect the Linear Interpolate Output to the Roughness Input of the 
Material Result Node. 
5. Now Create Two more Texture Sample Nodes like we did previously. 
Set the frst Texture Sample to Textures | VFX_LavaRock | NonLava_ 
Normal and Set the second Texture Sample to Textures | VFX_LavaRock 
| Lava_Normal. 
6. Create a Linear Interpolate Node and once again Connect the Texture 
Sample Nodes to the Linear Interpolate Inputs.

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### Breaking down the character movement (Page 151)

132 Enhancing Player Abilities
Below the Stick input group of Blueprint nodes, there is another comment block, called 
Mouse input, and it looks quite like the Stick input group: 
Figure 6.2 – Mouse input Events
Mouse input converts input from mouse movements (as opposed to controller axis sticks) 
into data, and then passes those values directly to the corresponding camera yaw and 
pitch input functions, without needing the same kind of calculations that are necessary for 
analog input.
Now, let's look at the group of nodes that manage player movement, as shown in this 
screenshot:

---

## Source: Mastering Technical Art in Unreal Engine (Greg Penninck)

### Blend Modes (Page 48)

29 
What Are Materials? 
 
 
 
 
 
 
 
 
 
 
 
 
• Post Process – Used to apply screen space effects after the scene has been 
rendered. These uses of these materials include adding outlines to objects 
when they are within an interactable distance or highlighting enemies 
through a wall. 
• User Interface – As the name suggests, these materials are for use in UMG 
to create materials for the UI. 
Each of the materials domains adjust which input pins are available on the material, 
for example, when selecting the Post Process material domain, all pins except for the 
Emissive Color input become unavailable but the material node looks the same as 
when using the Surface material domain. However, when using the User Interface 
material domain, we are presented with a completely different set of inputs including 
Final Color, Opacity or Opacity Mask (only one is available at any time, dependent 
on blend mode), and Screen Position. Because of this, it is important to learn which 
material domain and blend mode to use in a material. So, let’s take a look at the dif­
ferent Blend Modes. 
Blend Modes and Shading Models 
Each material domain has a selection of blend modes and shading models (not always 
available) which further determine which inputs are available for the material. 
Blend Modes 
The blend modes available depend on the material domain but the main ones we 
will look at for now are the available blend modes for the Surface material domain. 
These are: 
• Opaque – This is the standard material type, it, as the name suggests, is 
designed for opaque surfaces, surfaces where the light doesn’t pass through 
or enter. 
• Masked – This mode provides us with access to the Opacity Mask input. 
This allows us to defne areas of the material which are completely transpar­
ent using a black and white mask. Using this mode, each pixel can either be 
completely opaque or completely transparent, there is no range of opacity. 
The Details panel has a variable called Opacity Mask Clip Value which is 
used to convert any gradients in a texture (or math based input) connected 
to the Opacity Mask input, Anything above that value will be considered 
as white (opaque) anything below will be considered as black (transparent). 
• Translucent – This mode provides the range of opacity that the masked 
mode does not. With this mode, the Opacity Mask pin becomes grayed out 
and the Opacity pin becomes available. This mode allows for 256 levels of 
transparency using a grayscale mask input. 
• Additive – This mode takes the material and applies it on top of whatever is 
behind it (from the camera’s perspective). This works the same way as the

---

### Eroding Our Translucent VFX Master – Smooth Step (Page 133)

114 
Mastering Technical Art in Unreal Engine 
Emissive input with a Multiply Node to boost the visibility. Just remember to put it 
back after testing. Lowering the Erode value subtly below one will show your texture 
dissolving while maintaining a hard edge. Different textures will Erode at different 
values depending on their grayscale values, a bit of testing in Niagara later on is super 
helpful. 
Eroding Our Translucent VFX Master – Smooth Step 
1. In the Content Browser, navigate to the folder Content | Materials | 
Master. 
2. With the Material M_VFXTrans selected in the Content Browser, press 
Ctrl + D to create a Duplicate. Name this M_VFXTrans_SmoothStep. 
3. Double click on the Material M_VFXTrans_SmoothStep to open the 
Material Editor. 
4. Under the ParticleColor node in the Material Graph right click and Search 
for DynamicParameter. 
5. Select the DynamicParameter node and using the DetailsPanel type the 
name Erode into the Param Names Index [ 0 ] and set its Default Value for 
R to 0.75. 
6. Next to our DynamicParameter node, right click and Search for the node 
SmoothStep. 
7. Drag out from the R output from our ParticleTexture node and search for a 
OneMinus node. This should create a node labeled 1-x. 
8. Place the 1-x node just before our SmoothStep Node. Connect the 1-x output 
pin to the SmoothStep Min Input. 
9. Connect the Erode output from our DynamicParameter node to the Value 
input of the SmoothStep node. 
10. To the right of our SmoothStep node, hold M and left click to create a 
Multiply Node. 
11. Connect the R output from our ParticleTexture to the A input of the 
Multiply Node. 
12. Connect the output from the SmoothStep node to the B input of the Node. 
13. To the right of the Multiply node, right click and search for a Saturate node. 
14. Connect the output of the Multiply node into the Saturate node. This will 
ensure values are clamped between 0 and 1. 
15. Connect the output pin of the Saturate node into the Opacity input pin on 
the material output node. 
The completed Material can be seen in Figure 8.7. 
As per our previous erosion material, if you wish to preview the effect clearly in 
the Material Editor try redirecting the BaseColor input into the Emissive input with a 
multiply to boost the visibility. Just remember to put it back after testing. By lowering 
the Erode value less than one gently you should the texture dissolve with a soft edge. 
This approach while similar is better suited to softer effects such as smoke, where 
fades need to be more subtle.

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

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### Draining and regenerating stamina (Page 210)

Constraining player actions 191
Figure 8.12 – The ManageStaminaRecharge macro
4. Drag a wire from the In pin of the Inputs node and add a Branch node. 
5. Drag a wire from the Condition input pin of the Branch node and add a Nearly 
Equal (float) node. Enter the value 1.0 in the B input parameter of the Nearly 
Equal (float) node. We are using the Nearly Equal (float) node because it has an 
Error Tolerance property that is needed to compare values with floating-point 
precision.
6. Drag a wire from the A input parameter of the Nearly Equal (float) node and add 
a GET Player Stamina node.
7. Drag a wire from the True output pin of the Branch node and add a Clear Timer 
by Function Name node.
8. Drag a wire from the Function Name parameter of Clear Timer by Function 
Name and add a GET Stamina Manager Name node.
9. Connect the white output pin of Clear Timer by Function Name to the Out pin of 
the Outputs node.
10. Drag a wire from the False output pin of the Branch node and add a SET Player 
Stamina node. Connect the white output pin of SET Player Stamina to the Out pin 
of the Outputs node.
11. Drag a wire from the input pin of SET Player Stamina and add a Min (float) node. 
Enter the value 1.0 in the second input parameter of the Min (float) node. This 
node returns the lowest value of the input parameters. We use this node to ensure 
that Player Stamina will never be greater than 1.0.

---

## Source: Mastering Technical Art in Unreal Engine (Greg Penninck)

### Adding a Color Tint to the Material (Page 71)

52 
Mastering Technical Art in Unreal Engine 
Lerp nodes require three inputs (A, B and Alpha), to help explain the process, we 
will frst consider a lerp between pure red (255, 0, 0 or 1, 0, 0) and pure green (0, 255, 
0 or 0, 1, 0) with an alpha (or blend) value of 0.5. This means that for each channel of 
each input (pure red and pure green) is multiplied by 0.5 and then added together. So, 
we get a result of a greenish, yellow color (128, 128, 0 or 0.5, 0.5, 0). 
If we change the alpha value to 0.75 using the same two inputs, the pure red will be 
multiplied by 0.25 and the pure green will be multiplied by 0.75 and the results added 
together. This gives an output result of a green color (64, 191, 0 or 0.25, 0.75, 0). 
So far, these examples have been straight forward to see as we have been using 
inputs where we are always adding the multiplication result to a zero. But what about 
when there are multiple values in a channel to consider? For this example, we will just 
include the Unreal RGB to make things easier to read. 
Let’s consider two inputs as cyan (1, 0, 1) and yellow (1, 1, 0) with an alpha of 0.75. 
The alpha weighting means that the cyan channel values will be multiplied by 0.25 
giving us (0.25, 0, 0.25) and the yellow channel values will be multiplied by 0.75 
giving us (0.75, 0.75, 0). Adding these two results together will give us the output (1, 
0.75, 0.25), a sort of beige color. 
With a lerp operation, there is no risk of the values exceeding 1, assuming the input 
values are within the 0 to 1 range. 
Now that we’ve explained some material math and how multiply works, we can look 
at implementing it into the M_Coins material. 
Adding a Color Tint to the Material 
With the textures all available as parameters, next we are going to build in a color 
tint setup to allow us to tweak the visual result provided of the Base Color texture. 
This approach provides the artist with a color parameter which can be used to 
tweak the color of the texture, in this case, the coin. When combined with a gray‑
scale Base Color texture, this would allow us to have any color variation of the 
texture we desired. As we currently have a very yellow and brown texture for our 
gold coin, we are going to use this approach to tone down the texture a little with 
a shade of gray. 
We are going to be adding two nodes; a Multiply node, which performs the math­
ematical process on each pixel of the texture with the secondary input that will begin 
as a Constant 3 Vector node, which allows us to select a color value to use in the 
multiplication. 
So, let’s go back to the M_Coins material and add a color tint: 
1. Detach the Base Color Texture node from the Base Color pin by holding 
down ALT and left clicking the connection line. 
2. Hold down M on the keyboard and left click on the graph, this should cre­
ate a Multiply(0,1) node, you can also do this by right clicking and typing 
Multiply or by expanding the Palette tab on the right side of the Mater

---

