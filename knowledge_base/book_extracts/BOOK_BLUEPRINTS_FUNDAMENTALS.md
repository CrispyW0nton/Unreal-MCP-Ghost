# Book Knowledge: Blueprint Fundamentals

> Extracted from 2 books. Total 15 relevant sections.

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### Array (Page 351)

332 Data Structures and Flow Control
8. The nodes of steps 8–13 are to validate the Spawn Class and Target Points variables. 
Drag the Spawn Class variable from the My Blueprint panel, drop it into the 
EventGraph near Event BeginPlay, and select Get Spawn Class. 
9. Drag a wire from the Spawn Class node and add an Is Valid Class node.
10. Drag a wire from the Return Value pin of Is Valid Class and add an AND node. 
We are using the AND node because we will only spawn the Actor if both variables 
are valid. 
11. Drag the Target Points array variable from the My Blueprint panel, drop it into the 
EventGraph near the Spawn Class node, and select GET Target Points.
12. Drag a wire from the TargetPoints node and add an IS NOT EMPTY node. 
Connect the output pin of the IS NOT EMPTY node to the bottom input pin of the 
AND node. We need to check whether the array has elements.
13. Drag a wire from the output pin of the AND node and add a Branch node. Connect 
the white pin of Event BeginPlay to the white input pin of the Branch node.
14. The nodes of steps 14–18 are to spawn an Actor using the class stored in Spawn 
Class. Drag a wire from the True output pin of the Branch node and add 
a SpawnActor from the Class node.
15. Drag a wire from the Class input pin of the SpawnActor node and add a Get 
Spawn Class node.
16. Drag a wire from the Target Points node and add a Random Array Item node.
17. Drag a wire from the top output pin of the Random node and add 
a GetActorTransform node.
18. Connect the Return Value pin of GetActorTransform to the Spawn Transform 
input pin of the SpawnActor node.
19. Compile and save the Blueprint.
Now, we need to prepare the level to be able to test BP_RandomSpawner. 
Testing BP_RandomSpawner
We will add some instances of Target Point on the level. The BP_RandomSpawner 
instance will use the transform of one of these Target Points:
1. In the Level Editor, we will use Place Actors Panel to easily find the Target Point 
class. Click on the Create button on the toolbar to open a submenu, and then click 
on Place Actors Panel:

---

### Referencing Actors (Page 65)

46 Object-Oriented Programming and the Gameplay Framework
One advantage of inheritance is that we can create a function in the parent class and 
override it in the child classes with different implementations. For example, there can be 
a function named Fire in the Weapon parent class. The child classes inherit the Fire 
function, so the Shock Rifle class overrides the Fire function with a version that 
fires an energy beam, and the Rocket Launcher class overrides the Fire function to 
launch rockets. At runtime, if we have a reference to the Weapon class and call the Fire 
function, the instance class will be identified to run its version of the Fire function. 
Inheritance is also used to define the class type of a class since it accumulates all the types 
of its parent class. For example, we can say that an instance of the Shock Rifle class is 
of the Shock Rifle type and of the Weapon type. Because of this, if we have a function 
with a Weapon input parameter, it can receive instances of the Weapon class or any 
instances of its child classes.
These elementary concepts of OOP will help us understand the Gameplay Framework. 
Unreal Engine has some essential classes that are used in the development of games. These 
classes are parts of the Gameplay Framework. The main class of the Gameplay Framework 
is Actor.
Managing Actors
The Actor class contains all the functionality an object needs to exist in a Level. Therefore, 
the Actor class is the parent class for all objects that can be placed or spawned in a Level. 
In other words, any object that can be placed or spawned in a Level is a subclass of the 
Actor class. Most of the Blueprints that we'll create will be based on the Actor class itself 
or its child classes. Therefore, the features we will look at in this section will be useful for 
these Blueprints.
Referencing Actors
Variable types such as integer, float, and Boolean are known as primitive types because 
they only store simple values of the specified type. When working with objects or Actors, 
we use a type of variable known as an object reference. References in Blueprints allow 
different objects to talk to each other. We will explore this communication in greater detail 
in Chapter 4, Understanding Blueprint Communication.
For example, the following diagram represents instances of two Blueprint Classes in 
memory. The instance of the BP_Barrel Blueprint Class has an integer variable named 
Hit Counter, with a current value of 2. The other variable, named BP_Fire, is an 
object reference, which is referencing an instance of Blueprint Effect Fire. We can access 
the public variables and functions of another Blueprint using an object reference variable:

---

### Running the Behavior Tree in the AI Controller (Page 260)

Creating navigation behavior 241
9. The nodes of steps 9–11 set Patrol Point 2 as Current Patrol Point. Drag a wire from 
the True output pin of the Branch node and add a SET Current Patrol Point node.
10. Drag a wire from the input pin of the SET Current Patrol Point node and add a 
GET Patrol Point 2 node.
11. Drag a wire from the white output pin of the SET Current Patrol Point node and 
add the UpdatePatrolPointBB macro node.
12. The nodes of steps 12–15 are to check whether the enemy overlaps with Patrol 
Point 2. Drag a wire from the False output pin of the Branch node and add another 
Branch node.
13. Drag a wire from the Condition input pin of the second Branch node and add an 
Equal node.
14. Connect the top input pin of the Equal node to the Other Actor output pin of the 
Event ActorBeginOverlap node.
15. Drag a wire from the bottom input pin of the Equal node and add a GET Patrol 
Point 2 node.
16. The nodes of steps 16–18 set Patrol Point 1 as Current Patrol Point. Drag a wire 
from the True output pin of the second Branch node and add a SET Current Patrol 
Point node.
17. Drag a wire from the input pin of the new SET Current Patrol Point node and add 
a GET Patrol Point 1 node.
18. Connect the white output pin of the SET Current Patrol Point node to the input 
pin of the UpdatePatrolPointBB node.
19. Compile and save the Blueprint.
These are the actions needed in the BP_EnemyCharacter Blueprint to handle the patrol 
points. The next step is to modify the BP_EnemyController Blueprint to run the 
Behavior Tree. 
Running the Behavior Tree in the AI Controller
The AIController class has a function named Run Behavior Tree. It receives 
a Behavior Tree asset as a parameter. We created the BP_EnemyController Blueprint 
using AIController as the parent class to run our BT_EnemyBehavior Behavior Tree.
These are the steps to run the Behavior Tree:
1. Open the BP_EnemyController Blueprint.
2. In the EventGraph, drag a wire from the white execution pin of Event BeginPlay 
and add a Run Behavior Tree node.

---

## Source: Mastering Technical Art in Unreal Engine (Greg Penninck)

### Linear VFX Distortion Material (Page 238)

219 
The Fire Tornado 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
6. Then Drag out from the Texture Coordinate Node’s Output pin and search 
the Panner Node from the Popup Menu. 
7. Select the Panner Node and set the Speed X Value to −0.4 and the Speed 
Y Value to 0. 
8. Now right click in the Material Graph and search for a Time Node. Connect 
the Output Pin of the Time Node into the Time input of the Panner Node. 
9. Drag out from the Panner Node and from the menu search for a Texture 
Sample Parameter 2D Node. 
10. Select the Texture Sample Parameter 2D Node. Set the Parameter Name 
to ParticleTexture and Set the Texture property to Textures | EnergyOrb | 
Particle2. 
11. Select all of the nodes we have created and make a copy of the nodes below 
using Ctrl + C and Ctrl + V. 
12. Select the copied Texture Coordinate Node and set the X and Y Tiling 
Values to be 1.5 in the Detail Panel 
13. Select the copied Panner Node and change the Speed X Value to −0.1. 
14. Now Create a Multiply Node after the Texture Sample Parameter 2D 
Nodes using M and left click. Connect the RGB Output pins from both 
Texture Sample Parameter 2D Nodes into the A and B Inputs of the 
Multiply Node. 
15. Drag out from the Multiply and create a Component Mask from the Popup 
menu. Select the Mask and enable only the R & G Channels. 
16. Create an Add Node just after the Mask just A and left click. Connect the 
Output from the Mask Node into the B Input of the Add Node. 
17. Then create another Texture Coordinate Node by right clicking in the 
Material Graph and searching for the node. 
18. Connect the Output pin of the Texture Coordinate Node into the A Input 
of the Add Node. 
19. Review your progress against Figure 15.4 and Save your progress. 
We have now constructed the UV distortion part of the Material. To improve this sec­
tion further you could parametrize the Panner Node’s Speed inputs and add a Multiply 
Node after the Mask to adjust the strength of the panning coordinates. To fnish the 
Material, we’ll now move onto combining what we’ve done so far with Gradient and 
Particle Color nodes. 
1. Drag out of the Add Node and search for a Linear Gradient Node. 
2. Drag out of the Linear Gradient Node and search for a One Minus Node. 
3. Next, create two Multiply Nodes, using M and left click. Connect the One 
Minus Node into the A Input of Both Multiply Nodes. 
4. Now Create a Particle Color node by right clicking and searching for 
Particle Color. 
5. Connect the RGB Output Pin of the Particle Color Node into the B Input of 
one of the Multiply Nodes.

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### Making the enemies destructible (Page 293)

274 Upgrading the AI Enemies
5. Drag a wire from the Other output pin of the Event Hit node and add a Cast To 
FirstPersonProjectile node. Connect the white pins of Event Hit and Cast To 
FirstPersonProjectile.
6. Drag a wire from the white output pin of the Cast To FirstPersonProjectile node 
and add a Branch node.
7. Drag a wire from the Condition pin of the Branch node and add a Greater node.
8. Drag a wire from the top input pin of Greater node and add a Get Enemy Health 
node. Set a value of 1 in the bottom input of the Greater node.
9. Drag a wire from the True output pin of the Branch node and add a Decrement 
Int node.
10. Drag a wire from the input pin of the Decrement Int node and add a Get Enemy 
Health node.
11. Drag a wire from the False output pin of the Branch node and add a Spawn Actor 
from Class node. In the Class parameter, select the Blueprint_Effect_Explosion 
class, which is a blueprint from the starter content.
12. Drag a wire from the Spawn Transform parameter and add a GetActorTransform 
node.
13. The nodes of the second part of Event Hit are the same used in the 
BP_CylinderTarget blueprint:
Figure 10.23 – The second part of the Event Hit actions
14. Open the BP_CylinderTarget blueprint located in the Content > 
FirstPersonBP > Blueprints folder.
15. Select and copy the nodes shown in Figure 10.23, and then paste the nodes into the 
BP_EnemyCharacter blueprint.
16. Connect the white output pin of the Spawn Actor node to the white input of the 
Cast to FirstPersonCharacter node.
17. Compile, save, and then press Play to test.

---

### The execution path (Page 47)

28 Programming with Blueprints
The following screenshot shows the Event BeginPlay event of a Blueprint. In this example, 
the Blueprint has a string variable named Bot Name: 
1. The SET action assigns the Archon value to the Bot Name variable. 
2. The next action, Print String, displays the value that is received on the In String pin 
on the screen. These values that are passed to the functions are 
known as parameters. 
3. The In String pin is connected to a GET node of the Bot Name variable that returns 
the value of the Bot Name variable and passes it to the Print String function:
Figure 2.6 – Event BeginPlay with some actions 
4. To add the GET and SET Actions of a variable to Event Graph, simply drag the 
variable from the My Blueprint panel and drop it in Event Graph to show the GET 
and SET options. 
Other functions such as Print String are added from Context Menu that appears when 
you right-click on the Event Graph panel. The GET and SET actions can also be searched 
in Context Menu.
The white lines that connect the actions are also known as the execution path.
The execution path
The white pins of nodes are called execution pins. The other colored pins are the data 
pins. The execution of the nodes of a Blueprint starts with a red event node, and then 
follows the white wire from left to right until it reaches the last node.
There are some nodes that control the flow of execution of the Blueprint. These nodes 
determine the execution path based on conditions. For example, the Branch node 
has two output execution pins named True and False. The execution pin that will be 
triggered depends on the Boolean value of the Condition input parameter. The following 
screenshot shows an example of the Branch node:

---

### Instances (Page 63)

44 Object-Oriented Programming and the Gameplay Framework
Getting familiar with OOP
Let's learn about some elementary concepts of OOP, such as classes, instances, and 
inheritance. These concepts will help you learn about various elements of Blueprints 
Visual Scripting.
Classes
In OOP, a class is a template for creating objects and providing the initial values for state 
(variables or attributes) and implementations of behavior (events or functions).
Many real-world objects can be thought of in the same way, even if they are unique. As 
a very simple example, we can think of a person class. In this class, we can have attributes 
such as name and height, and actions such as move and eat. Using the person class, we can 
create several objects of this class. Each object represents a person with different values for 
their name and height attributes.
When we create a Blueprint, we are creating a new class that can be used to create objects 
in the levels of a game. As the following screenshot shows, the option that appears when 
creating a new Blueprint asset is Blueprint Class:
Figure 3.1 – Creating a Blueprint Class
Encapsulation is another important concept. It allows us to hide the complexity of a class 
when it is viewed from the point of view of another class. The variables and functions of 
a Blueprint class can be private, which means that they can only be accessed and modified 
in the Blueprint Class where they were created. The public variables and functions are 
those that can be accessed by other Blueprint Classes. 
Instances
An object created from a class is also known as an instance of that class. Each time 
you drag a Blueprint Class from Content Browser and drop it into the Level, you create 
a new instance of this Blueprint Class.
All instances are created with the same default values for their variables as were defined in 
the Blueprint Class. However, if a variable is marked as Instance Editable, the variable's 
value can be changed in the Level for each of the instances without affecting the values 
held by the other instances.

---

### Interpreting and storing the noise Event data (Page 288)

Making enemies hear and investigate sounds 269
Figure 10.16 – The On Hear Noise actions
3. Drag a wire from the white pin of the On Hear Noise (PawnSensing) node and add 
a Branch node. The next steps will create an expression that uses the VectorLength 
function to calculate the distance between the sound location and the enemy 
location. If the result of this expression is less than the value of Hearing Distance, 
then the True output pin of the Branch node is executed.
4. Drag a wire from the True pin of the Branch node and add the Update Sound BB 
macro node. Connect the Location pin of the On Hear Noise (PawnSensing) node 
to the Location pin of the Update Sound BB macro.
5. Drag a wire from the Condition input pin of the Branch node and add a Less node. 
6. Drag a wire from the bottom input pin of the Less node and add a GET Hearing 
distance node.
7. Right-click on the empty space of Event Graph and add a Get Controlled 
Pawn node to get the enemy instance that is being controlled by this 
BP_EnemyController.
8. Drag a wire from the Return Value pin of the Get Controlled Pawn node and add 
a GetActorLocation node to get the enemy location.
9. Drag a wire from the Location pin of the On Hear Noise (PawnSensing) node and 
add a Subtract node.
10. Connect the bottom input pin of the Subtract node to the Return Value pin of the 
GetActorLocation node.
11. Drag a wire from the output pin of the Subtract node and add a VectorLength 
node.
12. Connect Return Value of the VectorLength node to the top input pin of the Less 
node. Return Value of the VectorLength node is the distance between the location 
of the sound and the enemy location.
13. Compile and save the blueprint.

---

### A Blueprint Function Library example (Page 487)

468 Creating Blueprint Libraries and Components
15. Add two Random Integer in Range nodes to the EventGraph. Type 1 in the Min 
input parameter of the two nodes:
Figure 18.9 – Generating two random integer numbers
16. Drag wires from the Number Of Faces parameter and connect to the Max input pin 
of the two nodes. 
17. Connect the Return Value output pin of the first Random Integer in Range node 
to the Die 1 pin. Connect the Return Value output pin of the second Random 
Integer in Range node to the Die 2 pin.
18. Right-click the EventGraph and create an Add node. Connect the Return Value 
output pin of the first Random Integer in Range node to the top input pin of Add 
node. Connect the Return Value output pin of the second Random Integer in 
Range node to the bottom input pin of the Add node.
19. Connect the output pin of the Add node to the Sum pin of Return Node. Connect 
the True pin of the Branch node to the white pin of Return Node.
20. Compile and save the Blueprint.
With these steps, we have concluded creating the second function of the library. In the 
next section, we will create the third function, which will be done differently from the 
second function to show an alternative example. Then, we will test our Blueprint 
Function Library.

---

### Event Dispatchers (Page 105)

86 Understanding Blueprint Communication
10. Drag from the Blueprint_Effect_Sparks blue pin of the node and drop it in the 
graph to open Context Menu. Search for activate and choose Activate (Sparks). 
Connect the white pin of the OnActorBeginOverlap (TriggerBox) event to the 
white pin of the Activate function, as shown in the following screenshot:
Figure 4.26 – Activating Sparks when overlapping the TriggerBox
11. Compile the Level Blueprint and click the Play button of the Level Editor to test the 
Level. Move your character to the location of the Box Trigger to activate the sparks.
In this example, we saw how to add references and events of Actors in the Level Blueprint. 
This is the essence of Level Blueprint Communication. There is another form of 
communication between Blueprints and Level Blueprint called Event Dispatchers.
Event Dispatchers
An Event Dispatcher allows a Blueprint to inform other Blueprints when an Event 
happens. The Level Blueprint and other Blueprint classes can listen to this Event, and they 
may have different Actions that run when the Event is triggered.
We create Event Dispatchers in the My Blueprint panel. As an example, let's create a 
Blueprint named BP_Platform. When an Actor overlaps the BP_Platform Blueprint, 
it calls an Event Dispatcher called PlatformPressed. The Level Blueprint is listening 
for the PlatformPressed Event and spawns an explosion when this Event is triggered:
1. Create or use an existing project based on the Third Person template with the 
starter content.
2. Create a Blueprint and use Actor as the parent class. Name it BP_Platform and 
open it in the Blueprint Editor.

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

### A Blueprint Function Library example (Page 483)

464 Creating Blueprint Libraries and Components
Blueprint Macro and Function libraries
Sometimes, in a project, you identify a macro or function that can be used in several 
Blueprints. The Unreal Editor allows you to create a Blueprint Macro Library to gather the 
macros that you want to share between all Blueprints. In the same way, you can create 
a Blueprint Function Library to share utility functions between all Blueprints.
The menu options to create Blueprint Function Library and Blueprint Macro Library 
are in the Blueprints submenu that appears when creating an asset: 
Figure 18.1 – The menu options to create Blueprint Macro and Function Libraries
When creating a Blueprint Macro Library, you need to choose a Parent class. The macros 
of the library will have access to variables and functions of the Parent class selected, but 
the Macro Library can only be used by subclasses of the chosen Parent class. Selecting the 
Actor class will be the best option in most cases.
Let's create a Blueprint Function Library to see in practice how we can share functions 
between all Blueprints.
A Blueprint Function Library example
We will create a Blueprint Function Library for a dice roll named BP_DiceLibrary 
with three functions – RollOneDie, RollTwoDice, and RollThreeDice. All 
functions have the same input parameter named NumberOfFaces and return the result 
of each dice and the sum.
This Blueprint Function Library can be used when creating digital board games or in 
RPGs (Role-Playing Games) based on a dice roll.

---

### Defining the behavior of a Blueprint with events and actions (Page 44)

Defining the behavior of a Blueprint with events and actions 25
These attributes can be individually described as follows:
• Variable Name: This is the identifier of the variable.
• Variable Type: This specifies the type of values that can be stored in this variable.
• Instance Editable: When this box is checked, each copy of this Blueprint placed in 
the level can store a different value in this variable. Otherwise, the same initial value 
is shared by all copies, called instances. 
• Blueprint Read Only: If checked, the variable cannot be changed by Blueprint 
nodes.
• Tooltip: This contains information shown when the cursor hovers over the variable.
• Expose on Spawn: If checked, the variable can be set when spawning the Blueprint.
• Private: If checked, child Blueprints cannot modify it.
• Expose to Cinematics: If checked, this variable will be exposed to Sequencer.
• Category: This can be used to organize all variables in the Blueprint.
• Slider Range: This sets the minimum and maximum values that will be used by 
a User Interface (UI) slider to modify this variable.
• Value Range: This sets the minimum and maximum values allowed for this variable.
• Replication and Replication Condition: They are used in networked games.
• DEFAULT VALUE: This contains the initial value of the variable. The Blueprint 
must be compiled before you can set the default value.
Variables are used to represent the current state of a Blueprint, but the behavior is defined 
by events and actions, which will be discussed in the following section.
Defining the behavior of a Blueprint with 
events and actions
Most of the time, we will use Blueprints to create new Actors. In Unreal Engine, Actors are 
game objects that can be added to a level.
Unreal Engine informs the state of a game for an Actor using events. We define how an 
Actor responds to an event by using actions. Both events and actions are represented by 
nodes in the Event Graph panel.

---

### Step-by-step example (Page 58)

Organizing the script with macros and functions 39
Step-by-step example
Let's create a function step by step and execute it to see it in practice. The function name is 
CalculatePower. It receives the player's level as an input parameter and returns their 
power value using the following expression:
PowerValue = (PlayerLevel x 7) + 25
1. Click on the Content Drawer button to open the Content Browser, then click the Add 
button and select Blueprint Class.
2. On the next screen, choose Actor as the parent class.
3. Rename the Blueprint created to FunctionExample.
4. Double-click this Blueprint to open the Blueprint Editor.
5. In the My Blueprint panel, click the + button in the Functions category to create 
a function. Change the name of the function to CalculatePower.
6. Use the Details panel of this function to create an input parameter named 
PlayerLevel of Integer type and an output parameter named PowerValue of 
Integer type.
7. On the tab created for the CalculatePower function, create the expression seen in the 
following screenshot. You can add the nodes of operators by right-clicking on the 
graph to open Context Menu and search for add and multiply. To connect the nodes, 
click on one of the pins, drag the mouse and drop it on the other pin. Don't forget to 
insert the values 7 and 25 in the operator nodes. Compile the Blueprint.
Figure 2.24 – CalculatePower function
8. In the Event Graph, there is an Event BeginPlay node grayed out as it has no actions 
connected. The Event BeginPlay node will light up when you connect any node to 
it. Create the nodes seen in the next screenshot. Insert the value 3 in the Player Level 
parameter of the Calculate Power node. These nodes will calculate the PowerValue 
using the value 3 for Player Level. 
9. Click on the arrow of the Print String node to see more input parameters.

---

