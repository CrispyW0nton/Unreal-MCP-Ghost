# Book Knowledge: Blueprint Communication

> Extracted from 1 books. Total 15 relevant sections.

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### Casting in Blueprints (Page 96)

Casting in Blueprints 77
The following diagram represents a Blueprint called BP_GameModeWithScore. Game 
Mode Base is the parent class of this Blueprint. Based on the inheritance concept, we can 
use a variable of the Game Mode Base object reference type to reference an instance of 
BP_GameModeWithScore. However, this variable is unable to access the variables and 
functions of a subclass like those defined in the BP_GameModeWithScore Blueprint, 
because a Game Mode Base reference only knows the variables and functions that are 
defined in the Game Mode Base class:
Figure 4.11 – BP_GameModeWithScore inherits from Game Mode Base
Therefore, if we have a Game Mode Base object reference, we can try to cast this 
reference using the Cast To BP_GameModeWithScore function. If the instance 
is of the BP_GameModeWithScore type, then Cast To will succeed and return a 
BP_GameModeWithScore object reference that we can use to access the variables and 
functions of BP_GameModeWithScore.
Another use of the Cast To node is to safely test whether an object reference is of a desired 
type and this step-by-step example will illustrate both use cases:
1. Create or use an existing project, based on the Third Person template, with the 
starter content.
2. Click the Add button in Content Browser and choose the Blueprint Class option.
3. On the next screen, choose Game Mode Base as the parent class.
4. Name the Blueprint BP_GameModeWithScore and double-click it to open the 
Blueprint Editor.

---

### Making text bindings for the ammo and targets eliminated counters (Page 192)

Connecting UI values to player variables 173
Making text bindings for the ammo and targets 
eliminated counters
The ammo and targets eliminated counters will be represented by texts on the HUD. 
Follow these steps to bind the counters:
1. Click on the Designer button to return to the canvas interface once more. This 
time, we want to select the Ammo left text object in Hierarchy, which can be found 
under Weapon Stats.
2. In the Details panel, find the Bind button next to the Text field and create a new 
binding, as shown here:
Figure 7.32 – Creating a binding for Ammo left
3. We will follow the same pattern for this binding as we did for health and stamina. 
In the Get Ammoleft Text 0 graph view that appears, create a Get Player Character 
node, cast it using the Cast To FirstPersonCharacter node, and then drag from the 
As First Person Character pin to add a Get Player Current Ammo node.
4. Finally, attach both the cast node and the Player Current Ammo node to Return 
Node. You will notice that when you attach the Player Current Ammo output pin 
to the Return Value input pin, a new ToText (integer) node will be created and 
linked automatically. This is because Unreal Engine knows that for you to display 
a numerical value as text on the screen, it first needs to convert the number into 
a text format that the Widget knows how to display. The conversion node will be 
hooked up already, so there is no need to make further modifications. The following 
screenshot shows the nodes that are used in the binding:
Figure 7.33 – The value of the Player Current Ammo variable will be used as the Text of Ammo left

---

### The BP_Configurator Blueprint (Page 542)

The BP_Configurator Blueprint 523
Figure 20.14 – Configuring the user interface
The third output wire connects to nodes that perform the GUI event bindings. This 
is where the magic happens. We will see in the next section that the WBP Main GUI 
Widget Blueprint has an event dispatcher named Variant Selected. The nodes on the next 
screenshot bind a Custom Event named GUIVariantSelected to the Variant Selected 
event dispatcher:
Figure 20.15 – GUI event binding
When the user clicks on a button to activate a Variant, WBP Main GUI calls the Variant 
Selected event dispatcher. The GUIVariantSelected Custom Event will execute because it 
is bound to the Variant Selected event dispatcher.
For more information about event dispatchers and bindings, see Chapter 4, Understanding 
Blueprint Communication.

---

### Summary (Page 547)

528 Creating a Product Configurator Using the Variant Manager 
In the Create Event node, you will be able to select an event that has the same type of 
input parameters as the event dispatcher.
The last event dispatcher is from WBP_MainGUI, which binds a Custom Event to the 
Part Selected event dispatcher of WBP_MainSelector:
Figure 20.25 – WBP_MainGUI binding an event to Part Selected
The Variant Selected event dispatcher is the one that is bound in the BP_Configurator 
Blueprint.
In this section, we saw how UMG Widget Blueprints can be used together to create 
a dynamic and configurable interface.
Summary
In this chapter, we explained what a Product Configurator is, and we showed how to use 
the Product Configurator template. We learned how to use the Variant Manager panel to 
create Variants and Variant Sets.
We also learned how the BP_Configurator Blueprint stores all the information of the 
Level Variant Sets Actor needed to create a dynamic interface. We had an overview of the 
BP_Configurator functions and saw how to activate a Variant in a Blueprint.
Then, we saw how the WBP_MainGUI Widget uses the other UMG Widget Blueprints 
to create a user interface and saw how several event dispatchers were used to make the 
BP_Configurator act when a button was clicked.

---

### Event Dispatchers (Page 107)

88 Understanding Blueprint Communication
4. Compile the Blueprint. In the My Blueprint panel, create an Event Dispatcher and 
name it PlatformPressed. An Event Dispatcher can have input parameters. Let's 
create one to send a reference of the BP_Platform instance that was overlapped. 
In the Details panel, create a new parameter in the Inputs category, name it BP_
Platform, and set it as a BP Platform type object reference, as shown in the 
following screenshot:
Figure 4.28 – Creating an input parameter
5. Right-click Event Graph and add Event ActorBeginOverlap. Drag the 
PlatformPressed Event Dispatcher and drop it in Event Graph. Choose Call 
in the submenu. Right-click Event Graph, search for self, and select the Get a 
reference to self action. The Self Action returns a reference of the current instance. 
Connect the Actions, as shown in the following screenshot:
Figure 4.29 – Calling the Platform Pressed Event Dispatcher
6. Compile the Blueprint. In the Level Editor, drag BP_Platform from Content 
Browser and drop it in the Level to create an instance.

---

### Summary (Page 112)

Summary 93
12. Click the Play button of the Level Editor to test the Level. Move your character 
to the location of BP_Platform. When your character overlaps it, the 
PlatformPressed Event Dispatcher is triggered, and the Custom Event of BP_
Platform_Sparks is executed, activating the sparks:
Figure 4.37 – Touching the BP_Platform to activate the sparks
Summary
This was a practical chapter. We created step-by-step examples for each type of Blueprint 
Communication. We learned about how a Blueprint can reference another Blueprint using 
Direct Blueprint Communication and how to reference Actors on the Level Blueprint. 
We saw how to use casting to access variables and functions of a child class, and how to 
test whether an instance reference is of a certain class.
We learned about how to use an Event Dispatcher to inform us when an Event happens, 
and how to respond to this Event Dispatcher in the Level Blueprint. We also saw that 
we could bind an Event of another Blueprint to an Event Dispatcher.
This chapter concludes Section 1. We have now learned about the Blueprint fundamentals 
necessary to start scripting games and applications in Unreal Engine 5.
In Section 2, we will start to build a first-person shooter from scratch with step-by-
step tutorials. In the next chapter, we will create the project, add objects to the Level, 
manipulate the Materials of the objects, and add movement.

---

### Casting in Blueprints (Page 95)

76 Understanding Blueprint Communication
15. Click the Play button to see the BP_LightSwitch Blueprint in action. Every 
time your character overlaps the instance of BP_LightSwitch, it toggles the 
visibility of the selected Point Light. The following screenshot shows an example 
using the Third Person template. The Point Light variable is on the wall, and the 
BP_LightSwitch Blueprint is on the floor:
Figure 4.10 – Touching the BP_LightSwitch to turn on the light 
In this section, we learned how to create a variable that refers to an instance of another 
Blueprint. But sometimes we need to access attributes of the subclass of the instance being 
referenced. In this case, we need to cast the reference.
Casting in Blueprints
There is a node named Cast To that tries to convert reference variable types to new 
specified types. To understand casting, it is necessary to remember the concept of 
inheritance between classes, which we covered in Chapter 3, Actors and the Gameplay 
Framework.

---

### Casting in Blueprints (Page 100)

Casting in Blueprints 81
13. Right-click Event Graph and add Event ActorBeginOverlap. Other Actor is the 
instance that overlaps the BP_Collectable Blueprint. Drag from the blue pin of 
Other Actor and drop in the graph to open Context Menu. 
14. Choose the Cast To ThirdPersonCharacter action, as shown in the following 
screenshot. ThirdPersonCharacter is the Blueprint that represents the player in the 
Third Person template. We are using the Cast To action to test whether the instance 
referenced by Other Actor is the player:
Figure 4.18 – Casting the Other Actor reference
15. Right-click Event Graph and add the Get Game Mode function. Drag from the 
blue pin of Return Value and drop it in the graph to open Context Menu. Choose 
the Cast To BP_GameModeWithScore action. 
16. Drag from the blue pin of As BP Game Mode With Score, drop it in the graph, and 
choose the Add Game Score action in the Context Menu. Type 50 in the Score 
input parameter. 
17. Right-click Event Graph and add the DestroyActor function. Connect the white 
pins of the nodes. The content of Event ActorBeginOverlap is shown in the 
following screenshot:
Figure 4.19 – Actions of Event ActorBeginOverlap

---

### Creating bindings for health and stamina (Page 190)

Connecting UI values to player variables 171
Creating bindings for health and stamina
To create the bindings of the PlayerHealth and PlayerStamina variables with the 
progress bars' UI, follow these steps:
1. In the Content Browser, access the /Content/FirstPersonBP/UI folder and 
double-click on the HUD Widget Blueprint.
2. In the HUD UMG Editor, find the Hierarchy panel and click on the Health Bar 
object nested underneath the Player Stats Bars object.
3. With Health Bar now selected, locate the Percent field in the Progress category 
of the Details panel. Click on the Bind button next to Percent and select Create 
Binding, as shown in the following screenshot:
Figure 7.27 – Creating binding for the Health bar
4. The UMG Editor will switch from the Designer view to the Graph view. A new 
function has been created, allowing us to script a connection between the meter and 
the PlayerHealth variable. Right-click on any empty graph space and add a Get 
Player Character node.
5. Drag a wire from the Return Value output pin of the new node to empty space and 
add the Cast To FirstPersonCharacter node.
6. Break the execution pin connection between the Get Health Bar Percent 0 and 
Return Node nodes, and instead, connect Get Health Bar Percent 0 to 
our casting node, as shown here:
Figure 7.28 – Getting a reference to the FirstPersonCharacter instance

---

### Blueprint Communication using interfaces (Page 439)

420 Introduction to VR Development
To create a Blueprint Interface, follow these steps:
1. Click the Add button in the content browser, and in the Blueprints submenu, select 
Blueprint Interface:
Figure 16.23 – Creating a Blueprint Interface
2. The VR template has a Blueprint Interface named VRInteraction BPI in the 
Content > VRTemplate > Blueprints folder. Double-click it to open the 
Blueprint Interface Editor. The following screenshot shows the functions of the 
VRInteraction BPI interface:
Figure 16.24 – The VRInteractionBPI interface functions

---

### Blueprint Communication using interfaces (Page 440)

Blueprint Communication using interfaces 421
3. Open the Pistol Blueprint to see an example of an interface implementation. Click 
the Class Settings button of the Blueprint Editor. In the Details panel, go to the 
Interfaces category to see that the VRInteraction BPI interface was added to the 
Pistol Blueprint:
Figure 16.25 – Adding an interface
The Pistol Blueprint implemented the Trigger Pressed function of the 
VRInteraction BPI interface. Since the Trigger Pressed function does not have 
output parameters, it is implemented as an event:
Figure 16.26: Implementing a function of the interface

---

### Chapter 4: Understanding Blueprint Communication (Page 88)

4
Understanding 
Blueprint 
Communication
This chapter presents Blueprint Communication, which allows one Blueprint to access 
information from, and call the functions and events of, another Blueprint. In this chapter, 
we will explain Direct Blueprint Communication and show you how to reference Actors 
on a Level Blueprint. The concept of casting is explained in depth because it is an essential 
part of Blueprint Communication. We are also going to learn about Event Dispatchers, 
which enable communication between Blueprint classes and the Level Blueprint, as well as 
how to bind Events.
For each of these topics, we will do step-by-step examples to facilitate our understanding 
of the concepts and practice the creation of Blueprint scripts.
The following topics will be covered in this chapter:
• Direct Blueprint Communication
• Casting in Blueprints
• Level Blueprint Communication
• Event Dispatchers
• Binding Events

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

### Binding Events (Page 109)

90 Understanding Blueprint Communication
9. Compile the Level Blueprint and click the Play button of the Level Editor to test the 
Level. Move your character to the location where BP_Platform is. When your 
character overlaps it, the Level Blueprint will spawn an explosion at the same place:
Figure 4.32 – Touching the BP_Platform to spawn an explosion
We saw how the Level Blueprint can listen to an Event Dispatcher, but we can also make 
a Blueprint listen to an Event Dispatcher of another Blueprint by binding events.
Binding Events
There is a Bind Event node that binds one Event to another Event or to an Event 
Dispatcher, which can be in another Blueprint. When an Event is called, all the other 
Events that are bound to it are also called.
As an example, let's create a child Blueprint Class of Blueprint_Effect_Sparks. This 
new Blueprint binds an Event to the PlatformPressed Event Dispatcher of the BP_
Platform Blueprint that we created in the previous example:
1. Open the project used in the example of Event Dispatcher.
2. Create a Blueprint, expand the All Classes menu, and search for Blueprint_Effect_
Sparks, which we'll use as the parent class. Name it BP_Platform_Sparks and 
open it in the Blueprint Editor.

---

### Quiz (Page 113)

94 Understanding Blueprint Communication
Quiz
1. It is possible to call functions of another Blueprint using an object reference 
variable.
a. True
b. False
2. The Cast To node is used to convert an object reference to a reference of any 
other Blueprint Class. 
a. True
b. False
3. In the Level Blueprint, it is possible to create references to Actors that are in 
the Level.
a. True
b. False
4. The Level Blueprint cannot listen to an Event Dispatcher of a Blueprint class.
a. True
b. False
5. The Bind Event node can be used to bind an Event of a Blueprint to an Event 
Dispatcher of another Blueprint.
a. True
b. False

---

