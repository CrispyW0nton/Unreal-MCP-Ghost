# Book Knowledge: Animation Systems

> Extracted from 1 books. Total 15 relevant sections.

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### Skeleton and Skeletal Mesh (Page 450)

Animation overview 431
Animation Editor
There are five Animation Tools for working with Skeleton animation. These tools can be 
accessed by opening an associated asset. There are five buttons at the top right of each 
of the Animation Tools, as shown in the following screenshot, which are used to switch 
between the different tools:
Figure 17.2 – Using the buttons to switch between the Animation Tools
The Animation Tools accessed by the buttons are from left to right:
• Skeleton Editor: Used to manage Skeleton bones
• Skeletal Mesh Editor: Used to modify the Skeletal Mesh that is linked to the 
Skeleton and represents the Character visually
• Animation Editor: Allows the creation and modification of animation assets
• Animation Blueprint Editor: Allows the creation of scripts and State Machines to 
control the animations that the Character must use according to its current state
• Physics Asset Editor: Used to create physics bodies that will be used in simulations
Let's see the relationship between Skeleton and Skeletal Mesh.
Skeleton and Skeletal Mesh
A Skeletal Mesh is linked to a Skeleton. A Skeleton is a hierarchy of interconnected bones 
used to animate the polygon vertices of a Skeletal Mesh.
In Unreal Engine, Skeleton is a separate asset from Skeletal Mesh. As the animation is 
done in Skeleton, the animation can be shared by several other Skeletal Meshes that use 
the same Skeleton.

---

### Creating Animation Blueprints (Page 454)

Creating Animation Blueprints 435
The ThirdPerson_IdleRun_2D Blend Space mapped the following Speed values for each 
Animation Sequence:
• ThirdPersonIdle: 0.0
• ThirdPersonWalk: 93.75
• ThirdPersonRun: 375.0
In the example of Figure 17.6, the value used for Speed is approximately 234.3, then the 
resulting animation is using 50% of ThirdPersonWalk and 50% of ThirdPersonRun.
Animation in Unreal Engine is an extensive topic that requires the study of specific 
documentation aimed at animators. The purpose of this animation overview section 
was to introduce the main animation concepts so that you can work with Animation 
Blueprints, which we will introduce in the following section.
Creating Animation Blueprints
An Animation Blueprint is a specialized Blueprint with tools geared toward Character 
animation scripting. The Animation Blueprint Editor is like the Blueprint Editor, but it has 
some specific panels for animation.
Follow these steps to create an Animation Blueprint:
1. Click the ADD button in the Content Browser, and in the Animation submenu, 
select Animation Blueprint, as shown in the following screenshot:
Figure 17.7 – Creating an Animation Blueprint

---

### Animation Sequence (Page 451)

432 Animation Blueprints
Let's visualize the Skeleton used by the Third Person template. Access the Content > 
Mannequin > Character > Mesh folder and double-click on the UE4_Mannequin_
Skeleton asset to open the Skeleton Editor, as shown in the following screenshot:
Figure 17.3 – The Skeleton Editor
The left-side panel has the Skeleton Tree with the hierarchy of bones that are part of this 
Skeleton. You can select a bone and adjust its position and rotation relative to the Skeleton.
Animation Sequence
An Animation Sequence asset contains keyframes that specify bone transformations at 
specific times. It is used to play a single animation on a Skeletal Mesh.
The Animation Sequences available to a Skeleton can be viewed in the Asset Browser of 
the Animation Editor. The following screenshot shows the Animation Sequences of the 
Third Person template:

---

### Creating Animation Blueprints (Page 455)

436 Animation Blueprints
2. In the next window, you need to select the target Skeleton. The animation assets 
and the Animation Blueprint are linked to a specific Skeleton. Optionally, you can 
select a different parent class instead of the default class. For this example, do not 
select a parent class and select UE4_Mannequin_Skeleton, which is in the /Game/
Mannequin/Character/ path:
Figure 17.8 – Selecting the target Skeleton
3. Give a name to the Animation Blueprint created in the Content Browser and 
double-click it to open the Animation Blueprint Editor.
The Animation Blueprint Editor has two types of graphs that work together to create the 
animation. The EventGraph is the same as the one from the Blueprint Editor, but with 
some specific nodes for animation. In the AnimGraph, we can create State Machines and 
use nodes to play Animation Sequences and Blend Spaces.
Let's start by analyzing the EventGraph.

---

### Modifying the Animation Blueprint (Page 471)

452 Animation Blueprints
8. Before closing the Blueprint, let's look at where we associate the Character 
Blueprint with the Animation Blueprint. In the Components panel, select Mesh 
(CharacterMesh0) (Inherited). In the Details panel, in the ANIMATION category, 
Animation Mode must be set to Use Animation Blueprint and Anim Class must 
specify the Animation Blueprint being used: 
Figure 17.37 – Specifying the Animation Blueprint used by the Character 
9. Compile, save, and close the Blueprint.
We have completed the Character Blueprint adjustments. Now, we can add the prone 
Animation States to the Animation Blueprint.
Modifying the Animation Blueprint
We will also add the Proning Boolean variable to the Animation Blueprint to be able to 
use it in the Transition Rules. Then, we will add three states to the State Machine.
Follow these steps to modify the Animation Blueprint:
1. Double-click on the UE4ASP_HeroTPP_AnimBlueprint asset located in the 
Content > AnimStarterPack folder to open the Animation Blueprint Editor.
2. In the My Blueprint panel, create a variable named Proning of the Boolean type. 
We need to create this variable in the Animation Blueprint because it will be used in 
the state Transition Rules:

---

### Chapter 17: Animation Blueprints (Page 448)

17
Animation 
Blueprints
Part 4 presented data structures, flow control, math nodes, Blueprints tips, and an 
introduction to virtual reality development.
In Part 5, we will look at Animation Blueprints, Blueprint libraries and components, 
procedural generation, and the Product Configurator template.
This chapter presents the main elements of the Unreal Engine animation system, such as 
Skeleton, Skeletal Mesh, Animation Sequences, and Blend Spaces. It shows how to script 
an Animation Blueprint using EventGraph and AnimGraph. It also explains how State 
Machines are used in an animation and how to create new states for an animation.
These are the topics covered in this chapter:
• Animation overview
• Creating Animation Blueprints
• Exploring State Machines
• Importing the Animation Starter Pack
• Adding Animation States

---

### Summary (Page 479)

460 Animation Blueprints
8. Click the Play button of the Level Editor. Use the C key to crouch and the X key 
to prone:
Figure 17.52 – Press the X key to prone
The Animation Blueprint has specific tools that allow you to control complex animations 
by breaking them into states. A great advantage of Animation Blueprints is the separation 
of animation logic and game logic in a project.
Summary
This chapter presented some animation concepts, focusing on Animation Blueprints. 
We looked at Animation Editor, Skeleton, Skeletal Mesh, Animation Sequence, and 
Blend Space.
This chapter showed how to use the EventGraph and AnimGraph of an Animation 
Blueprint. We also learned how to create State Machines in the AnimGraph.
We also saw a practical example of how to add states to the Character of the Animation 
Starter Pack.
In the next chapter, we will learn how to create Blueprint libraries and components that 
can be used throughout a project.

---

### EventGraph (Page 456)

Creating Animation Blueprints 437
EventGraph
We use the EventGraph of an Animation Blueprint to get data from the Pawn/Character 
that is using the Animation Blueprint instance and update the variables of the Animation 
Blueprint. The EventGraph has two nodes already added to the graph:
Figure 17.9 – Animation Blueprint Editor EventGraph
These are descriptions of the nodes:
• Event Blueprint Update Animation: This event is executed at every frame, allowing 
for the updating of variables used by the animation. The Delta Time X parameter is 
the amount of time elapsed since the last frame.
• Try Get Pawn Owner: This function tries to get the reference of the Pawn or 
Character that is using the Animation Blueprint instance. We need this function so 
we can get Character data to use in the animation.
If you need to do some initialization on the animation, you can use Event Blueprint 
Initialize Animation:
Figure 17.10 – Event used to initialize animation
As an example of using the EventGraph, let's create the Speed variable and update its 
value using data from the Pawn/Character that is using the Animation Blueprint instance.

---

### Exploring State Machines (Page 461)

442 Animation Blueprints
Exploring State Machines
A State Machine in the AnimGraph allows you to organize the animation into a series of 
states. To exemplify this, we will create a State Machine with two states: idle and moving.
We need to define Transition Rules to control the transition from one state to another.
Follow these steps to create the State Machine:
1. Remove the other animation nodes and leave only the Output Pose node in 
the AnimGraph.
2. Right-click on the AnimGraph, search for state machine, and select Add New 
State Machine…:
Figure 17.18 – Adding a State Machine
3. Rename the State Machine to Char States. You can rename it in the Details 
panel. Connect the white icon of the State Machine to the white icon of the Output 
Pose node:
Figure 17.19 – Connecting the State Machine to the Output Pose node

---

### Blend Space (Page 453)

434 Animation Blueprints
The Asset Browser of the Animation Editor lists other types of animation assets besides 
Animation Sequences. For example, in Figure 17.4, the ThirdPerson_IdleRun_2D asset 
has a different-colored icon because it is a Blend Space, which we will see in the 
next section. 
Blend Space
Blend Space is an asset type that allows the blending of animations based on one or two 
parameter values. To facilitate understanding, let's analyze the ThirdPerson_IdleRun_2D 
asset, which is a Blend Space based on one parameter.
Double-click on the ThirdPerson_IdleRun_2D asset in the Asset Browser to open it in 
the Viewport. This Blend Space has a parameter named Speed and uses three Animation 
Sequences, which are ThirdPersonIdle, ThirdPersonWalk, and ThirdPersonRun. Hold 
the Shift key to move the preview value of the Speed parameter, which is represented by 
the green plus icon:
Figure 17.6 – Blending the walking and running Animation Sequences

---

### AnimGraph (Page 459)

440 Animation Blueprints
There is an Asset Browser available in the bottom right of the Animation Blueprint Editor:
Figure 17.14 – Asset Browser in the Animation Blueprint Editor
You can drag an animation asset from the Asset Browser and drop it in the AnimGraph 
to create the equivalent node. In the example shown in the following screenshot, the 
ThirdPersonRun Animation Sequence was dropped in the AnimGraph to create the 
Play ThirdPersonRun node. You need to connect the white character icon of the Play 
ThirdPersonRun node to the white character icon of the Output Pose node and compile 
the Animation Blueprint to preview the animation in the Viewport:
Figure 17.15 – Playing the ThirdPersonRun animation in the Animation Blueprint Editor
To create a Blendspace Player node, just drag a Blend Space asset, such as ThirdPerson_
IdleRun_2D, and drop it in the AnimGraph. In the following screenshot, the value of the 
Speed variable is being used as the parameter of the Blend Space:

---

### Animation overview (Page 449)

430 Animation Blueprints
By the end of the chapter, you will know how to use Animation Blueprints and how to add 
Animation States.
Animation overview
The animation system in Unreal Engine is very flexible and powerful. It consists of 
numerous tools and editors that work together. In this chapter, we will look at the main 
concepts of animation in Unreal Engine with a focus on Animation Blueprints.
We will start with a project using the Third Person template to see animation concepts and 
explore the Animation Editor.
Follow these steps to create the project:
1. Create a project using the Third Person template with starter content:
Figure 17.1 – Creating a project using the Third Person template
2. Press the Play button to try the default gameplay that is built into the Third Person 
template. You can move the player Character using the WASD keys and look around 
by moving the mouse. Press the spacebar to make the Character jump.
Now that we have an example project, let's explore the Animation Editor.

---

### Importing the Animation Starter Pack (Page 465)

446 Animation Blueprints
Importing the Animation Starter Pack
In the next sections, we will use the Animation Starter Pack because it has more 
animations available.
Follow these steps to import the Animation Starter Pack:
1. Access the Epic Games Launcher and go to Unreal Engine | Library | Vault. Search 
for Animation Starter Pack and click the Add To Project button: 
Figure 17.27 – Adding the Animation Starter Pack to a project
Note
If you don't have the Animation Starter Pack installed, follow the instructions 
in Chapter 9, Building Smart Enemies with Artificial Intelligence, to install it. 
2. Select the project you created for this chapter. A folder called AnimStarterPack 
will be added to the Content folder of your project.
3. Look in the Viewport of the Level Editor and delete the ThirdPersonCharacter 
instance that is in the Level. We will use the Character of the Animation Starter Pack.
4. Open the ThirdPersonGameMode Blueprint located in the Content > 
ThirdPersonBP > Blueprints folder. The Blueprint will open as a data-only 
Blueprint.
5. In the CLASSES category, change Default Pawn Class to Ue4ASP_Character, which 
is the Character Blueprint of the Animation Starter Pack:

---

### Table of Contents (Page 12)

Table of Contents xi
Debug lines 
 376
Example of vectors and trace nodes 
 376
Summary 
 380
Quiz 
 381
15
Blueprints Tips
Blueprint Editor shortcuts 
 384
Blueprint best practices 
 390
Blueprint responsibilities 
 390
Managing Blueprint complexities 
 393
Using miscellaneous 
Blueprint nodes 
 399
Select 
 399
Teleport 
 400
Format Text 
 401
Math Expression 
 402
Set View Target with Blend 
 402
AttachActorToComponent 
 403
Enable Input and Disable Input 
 404
The Set Input Mode nodes 
 404
Summary 
 405
Quiz 
 406
16
Introduction to VR Development
Exploring the VR template 
 408
The VRPawn Blueprint 
 409
Teleportation 
 412
Object grabbing 
 416
Blueprint Communication 
using interfaces 
 419
Interacting with the menu 
 422
Summary 
 425
Quiz  
 425
Part 5: Extra Tools
17
Animation Blueprints
Animation overview 
 430
Animation Editor 
 431
Skeleton and Skeletal Mesh 
 431
Animation Sequence 
 432
Blend Space 
 434
Creating Animation Blueprints  435
EventGraph 
 437
AnimGraph 
 439
Exploring State Machines 
 442
Importing the 
Animation Starter Pack 
 446

---

### AnimGraph (Page 460)

Creating Animation Blueprints 441
Figure 17.16 – Playing a Blend Space in the Animation Blueprint Editor
After compiling the Animation Blueprint, you can modify the value of the Speed 
variable in the Anim Preview Editor, located at the bottom right of the Animation 
Blueprint Editor:
Figure 17.17 – Anim Preview Editor
Assign different values to the Speed variable between 0 and 375 and see the resulting 
animation in the Viewport.
We saw how to connect the animation nodes directly to the Output Pose node, but the 
AnimGraph was created with a State Machine in mind. We will discuss State Machines in 
the following section.

---

