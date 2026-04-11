# Book Knowledge: UI & UMG Widgets

> Extracted from 2 books. Total 15 relevant sections.

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### Displaying the HUD (Page 188)

Creating simple UI meters with UMG 169
Important Information
In most cases, Event BeginPlay will call the subsequent Actions as soon as 
the game is started. If the Blueprint instance isn't present when the game 
starts, then instead, it will trigger as soon as the instance is spawned. Since the 
FirstPersonCharacter player instance is present as soon as 
the game begins, attaching the displaying logic to this event will create the 
HUD immediately.
4. Drag a wire from the output execution pin of Event BeginPlay and add a Create 
Widget node. Within the node, you will see a drop-down menu labeled Class. This 
is our opportunity to use the Widget Blueprint we created. Recall that we named 
our Widget Blueprint HUD. If you click the drop-down menu, then you will see 
the HUD option. Select it to have the player Character Blueprint generate the UI 
elements you created. The following screenshot shows the Create HUD Widget 
node associated with our HUD Widget Blueprint:
Figure 7.25 – Creating an instance based on the HUD Widget Blueprint
5. Although we now have a Widget generated when the game starts, there is a final 
step required to get the Widget containing our UI elements to appear on the 
screen. Drag the Return Value output pin into empty grid space and add an Add to 
Viewport node.

---

### UMG Widget Blueprints (Page 543)

524 Creating a Product Configurator Using the Variant Manager 
The GUIVariantSelected Custom Event calls the Activate Variant function, using the 
selected Variant Set and Variant Index parameters. The Switch On function of the 
Variant is used to activate the Variant:
Figure 20.16 – The Activate Variant function
The dynamic interface is created by some UMG Widget Blueprints that work together and 
use the variables from BP_Configurator.
UMG Widget Blueprints
There are five UMG Widget Blueprints used in the Product Configurator interface. For 
more information about UMG, see Chapter 7, Creating Screen UI Elements. 
These are the UMG Widget Blueprints:
• WBP_MainGUI: The main Widget Blueprint that contains the other widgets.
• WBP_MainSelector: This is the Widget responsible for reading the Level Variant 
Sets and creating the corresponding buttons. 
• WBP_VariantRibbonSelector: This Widget is used to show the Variant options of 
the selected Variant Set.
• WBP_PopupSelector: This Widget is similar to WBP_VariantRibbonSelector, 
but it is used for camera and environment lighting. 
• WBP_Button: This Widget represents the button used to select a Variant or 
a Variant Set.

---

### Creating simple UI meters with UMG (Page 173)

154 Creating Screen UI Elements
Creating simple UI meters with UMG
In this section, we will learn how to use the UMG Editor to create the UI elements that 
we will use in our game and how to position them on the screen.
The UMG Editor is a visual UI authoring tool. We can use the UMG Editor to create 
menus and a Heads-Up Display (HUD). A HUD is a transparent display that provides 
information without requiring the user to look away from the main view. It was initially 
developed for military aviation. The acronym HUD has become common in games 
because the information is displayed on the game screen. We want to show meters on the 
HUD with the amounts of health and stamina the player currently possesses. These meters 
that appear on the HUD are known as UI meters.
The health and stamina UI meters will look like this:
Figure 7.1 – The Health and stamina UI meters
The number of targets eliminated and the ammo of the player will be displayed using text:
Figure 7.2 – Targets eliminated and ammo counters
To create a HUD that will display the UI meters for health and stamina, we will first need 
to create variables within the player character that can track these values. We will also 
create the variables that will count the targets eliminated and the ammo of the player.
Follow these steps to create the variables:
1. In the Content Browser, access the /Content/FirstPersonBP/Blueprints 
folder and double-click on the FirstPersonCharacter Blueprint.
2. Find the Variables category of the My Blueprint panel in the Blueprint Editor. Click 
on the + sign to add a variable, name it PlayerHealth, and change Variable Type 
to Float.
3. Follow the same steps again to create a second Float variable called 
PlayerStamina.
4. Next, create a third variable, but this time, select Integer as Variable Type and 
name it PlayerCurrentAmmo.

---

### Interacting with the menu (Page 441)

422 Introduction to VR Development
4. In this event, the Pistol Blueprint spawns an instance of the Projectile Blueprint. 
The Trigger Pressed function is called by the VRPawn Blueprint in the 
InputAction TriggerLeft and InputAction TriggerRight events:
Figure 16.27 – The VRPawn Blueprint calls the Trigger Pressed function of the interface
The VRPawn Blueprint gets the Actor owner of GrabComponent and calls the Trigger 
Pressed function using the Actor owner reference. If the Actor has an implemented 
VRInteraction BPI interface, then Trigger Pressed is executed. Nothing happens if the 
Actor did not implement the VRInteraction BPI interface. 
In the next section, we will see how the user interacts with the menu in the virtual world.
Interacting with the menu
The VR template has a menu system that is activated by pressing the Menu button on 
the motion controller. The menu system is implemented by the Menu Blueprint and 
the WidgetMenu Blueprint. Both Blueprints are in the Content > VRTemplate > 
Blueprints folder.
The events of VRPawn that deal with the menu are InputAction MenuToggleLeft and 
InputAction MenuToggleRight, which are triggered by the Menu button of the motion 
controllers. The Menu button is used to show and hide the menu.
The next screenshot shows the InputAction MenuToggleRight event that executes the 
Toggle Menu function of VRPawn:

---

### Creating a win menu screen (Page 228)

Setting a gameplay win condition 209
13. You will be taken to the Graph view, where an On Clicked (Btnrestart) node will 
appear. Drag from the output pin of On Clicked (Btnrestart) onto Graph and add 
an Open Level (by Object Reference) node. In the Level parameter, select the level 
we are using, which is FirstPersonExampleMap. This node will reload the level 
when the player clicks on the button, resetting all aspects of the level, including 
targets, ammo collectibles, and the player.
14. Drag from the output pin of Open Level (by Object Reference) onto Graph and 
add a Remove from Parent node. This node removes the WinMenu widget from 
the view. We want the menu to go away once the level is reset:
Figure 8.38 – The actions of the Restart button
15. We will do similar steps for the Quit button. Return to the Designer view and click 
on the Btn quit object, scroll down to the bottom of the Details panel, and click on 
the + button next to the On Clicked event to add an event.
16. You will be taken to the Graph view, where an On Clicked (Btnquit) node will 
appear. Drag from the output pin of On Clicked (Btnquit) onto Graph and add 
a Quit Game node so that the player can shut down the game by clicking the 
Quit button:
Figure 8.39 – The action of the Quit button
17. Compile, save, and close the UMG editor.

---

### Drawing shapes with Widget Blueprints (Page 175)

156 Creating Screen UI Elements
Drawing shapes with Widget Blueprints
The UMG Editor uses a specialized type of Blueprint called a Widget Blueprint. Since 
the First Person template has no UI elements by default, we should create a new folder to 
store our GUI work. Follow these steps to create a folder and a Widget Blueprint:
1. In the Content Browser, access the /Content/FirstPersonBP/ folder. 
Right-click in an empty space next to the list of folders and select the New Folder 
option. Name the folder UI:
Figure 7.5 – Creating the UI folder
2. Open the UI folder you just made, and then right-click in the empty folder space. 
Go to User Interface | Widget Blueprint and name the resulting Blueprint HUD: 
Figure 7.6 – Creating a Widget Blueprint
3. Double-click on this Blueprint to open the UMG Editor. We will use this tool to 
define how our UI is going to look on the screen.

---

### UMG Widget Blueprints (Page 544)

UMG Widget Blueprints 525
The next screenshot shows the relationship between some of the Widgets:
Figure 20.17 – The relationship of the Widgets
The Widget Blueprints are located in the Content > ProductConfig > UMG 
folder. Let's start by looking at WBP_MainGUI. The following screenshot is from its 
Hierarchy panel:
Figure 20.18 – The WBP_MainGUI Hierarchy panel
WBP_MainGUI uses two WBP_Button Widgets and two WBP_PopupSelector Widgets 
to manage the camera and environment lighting options. MainPartVarSelector is a 
WBP_MainSelector Widget that manages the Variants of the product.
The buttons of the Variant Sets and each Variant are created in Event Construct of the 
WBP_MainSelector Widget. The Populate Options function creates the buttons using 
the thumbnails from the Level Variant Sets:
Figure 20.19 – Event Construct of WBP_MainSelector

---

### Interacting with the menu (Page 443)

424 Introduction to VR Development
Double-click WidgetMenu to open the UMG Editor:
Figure 16.30 – The WidgetMenu in the UMG editor
In the Graph tab of the UMG Editor, we can see the On Clicked events of the buttons. 
The On Clicked (RestartButton) event uses the Open Level function to reload the Level:
Figure 16.31 – The On Clicked (RestartButton) event
The ExitButton button has the Real Life label. The On Clicked (ExitButton) event uses 
the Quit Game function to exit the application:
Figure 16.32 – The On Clicked (ExitButton) event

---

### Connecting UI values to player variables (Page 189)

170 Creating Screen UI Elements
6. Create a comment around the three nodes. Label the comment Draw HUD on 
Screen. The nodes should appear as follows:
Figure 7.26 – The Add to Viewport node shows the Widget Blueprint on screen
7. Now, compile, save, and click on Play to test the game. 
We've learned how to create text elements and progress bars in the UMG Editor. 
We've also learned how to use containers, such as horizontal and vertical boxes, 
to organize UI elements on screen.
When playing the game, you should see the two meters representing the player's health 
and stamina, as well as numerical counters for ammo and eliminated targets. But as 
you shoot from your gun, you may notice one very important problem – none of the UI 
values change! We will address this missing component in the next section.
Connecting UI values to player variables
To allow our UI elements to pull data from our player variables, we need to revisit the 
HUD Widget Blueprint. To get our UI to update with player data, we will create 
a binding. Bindings give us the ability to tie variables or functions of a Blueprint to 
a Widget. Whenever the variable or function is updated, that change is reflected in the 
Widget automatically. 
So, instead of manually updating both the player's health stats and our Widget every time 
the player takes damage (so that the health meter display changes), we can bind the meter 
to the PlayerHealth player variable. Then, only one value will need to be updated.

---

### Adding objects to our Level (Page 118)

Adding objects to our Level 99
Now that we have a template selected and the project settings set up the way we like, we 
can create the project. To do so, follow these steps:
1. Click on the blue Create button. After the engine is done with initializing the assets 
and setting up your project, the Unreal Editor will open the Level Editor.
2. Press the Play button to try the default gameplay that is built into the First Person 
template. You must click on the viewport for the game to start reacting to input. 
You can move the player character using the W, A, S, and D keys and look around 
by moving the mouse. You can fire projectiles using the left mouse button. The 
projectile will affect some physics objects in the Level. Try shooting at the white 
boxes scattered around the Level and observe them moving.
3. In Play mode, the Play button will be replaced with a Pause button, a Stop button, 
and an Eject button. You can press Shift + F1 to access the mouse cursor and click 
the Pause button to temporarily halt the play session, which can be useful when 
you want to explore the properties of an interaction or Actor that you have just 
encountered during gameplay. 
Clicking the Stop button ends the play session and takes you back to editing mode. 
Clicking the Eject button detaches the camera from the player, allowing you to move 
freely through the Level. Go ahead and try playing the game before we continue.
Adding objects to our Level
Now, we want to start adding our own objects to the Level. Our goal is to create a simple 
target Actor that changes color when shot with the included gun and projectile. We can 
create a simple Actor by following these steps:
1. In the Level Editor, click the Create button located on the toolbar. Hover over 
Shapes to display a submenu and drag Cylinder and drop it somewhere in the Level 
to create an instance:
Figure 5.3 – Adding a Cylinder shape to the Level

---

### Chapter 7: Creating Screen 
UI Elements (Page 172)

7
Creating Screen 
UI Elements
At the core of any gaming experience is the method game designers use to communicate 
the goals and rules of the game to the player. One method of doing this, which is common 
across all forms of games, is using a Graphical User Interface (GUI) to display and 
broadcast important information to the player. In this chapter, we will set up a GUI that 
will track the player's health and stamina, and we will set up counters that display the 
targets eliminated and the ammo of the player. You will learn how to set up a basic User 
Interface (UI) using Unreal's GUI Editor and how to use Blueprints to tie that interface to 
gameplay values. We will create UI elements using the Unreal Motion Graphics (UMG) 
UI Designer.
In the process, we will cover the following topics:
• Creating simple UI meters with the UMG
• Connecting UI values to player variables
• Tracking the ammo and eliminated targets
By the end of the chapter, you will know how to use the UMG Editor to create progress 
bars that display the status of health and stamina and also know how to display the 
number of targets eliminated and the ammo of the player.

---

### Creating a win menu screen (Page 223)

204 Creating Constraints and Gameplay Objectives
10. We will follow the same pattern for this binding as we did in the other HUD 
bindings we created in Chapter 7, Creating Screen UI Elements. Add a Get Player 
Character node, cast it using the Cast To FirstPersonCharacter node, and then 
drag from the As First Person Character pin to add a Get Target Goal node. 
Finally, attach both the Cast To node and the Target Goal node to Return Node:
Figure 8.29 – The value of the Target Goal variable will be shown on the HUD
11. Compile, save, and play the game.
You should see that the target counter increments as targets are destroyed. The Target 
Goal shown on the right of the target counter does not change. Now, we need to ensure 
that the player gets feedback when they reach their target goal.
Creating a win menu screen
To give the player feedback once they have won the game, we are going to create 
a WinMenu screen that will appear upon destroying the required number of targets. 
To create this WinMenu, we are going to need another Blueprint widget, like the one 
we created for the HU:
1. In the Content Browser, access the /Content/FirstPersonBP/UI folder and 
then right-click in the empty folder space. Go to User Interface | Widget Blueprint 
and name the resulting Blueprint WinMenu:
Figure 8.30 – Creating a Widget Blueprint

---

### Creating a pause menu (Page 320)

Pausing the game and resetting the save file 301
Pausing the game and resetting the save file
We will create PauseMenu, which will present the player with options to resume playing 
the game, reset the game to round one, or quit the application.
Creating a pause menu
PauseMenu is like our LoseMenu. So, we will use it as a template. The following screenshot 
shows the elements we want in PauseMenu:
Figure 11.20 – Pause menu elements
 Follow these steps to create PauseMenu:
1. In the Content Browser, access the Content > FirstPersonBP > UI folder. 
Right-click on LoseMenu and select the Duplicate option. 
2. Name this new Blueprint Widget PauseMenu.
3. Select the text displaying You Lose! and, in the Details panel, change the Text field 
to Paused and change the Color and Opacity to a blue color:
Figure 11.21 – Setting the message of PauseMenu

---

## Source: Mastering Technical Art in Unreal Engine (Greg Penninck)

### Fireworks – Trail Emitter (Page 204)

185 
Magical Spells and Fireworks 
distance that you’ll view this effect from any changes would need to be bold to stand 
out. We’ll now move onto our Trail Emitter. 
Fireworks – Trail Emitter 
The Trailer Emitter, consists of a spawned particle that is quite short lived. It follows 
the Head Emitter with a subtle intensity across the sky before the Firework explodes. 
To create interest with the Trail Emitter you could look into varying the colors and 
add noise to the particle’s position to make the trails cool. 
Let’s get started! 
1. In the Content Browser, navigate to the Content | VFX folder. 
2. Right click anywhere in the VFX Folder and create a FX\Niagara 
Emitter asset. From the pop up menu choose to create a new Emitter 
and set the Template to be Single Looping Particle and Label the asset 
FireworksTrail_Emitter. 
3. Double click the FireworksTrail_Emitter to open the Niagara Editor. 
4. Delete or Disable the Spawn Instantaneous Module. 
5. Select the Initialize Particle Module, change the Life Time to a Range 
Float Range. Set the Lifetime Min to 0.1 and the Lifetime Max to 0.6. Set 
the Uniform Sprite Size to a Range Float Range. Set the Uniform Sprite 
Size Min to 8 and the Uniform Sprite Size Max to 12. This will make the 
particles very short lived and smaller than the Fireworks Head Particle. 
6. Click the Green + Button next to the Particle Update Stage and select Add 
Scale Sprite Size Module from the Menu. Set the Template to Smooth 
Ramp Down. 
7. Click the Green + Button next to the Particle Update Stage and select Add 
Curl Force Noise Module from the Menu. Set Noise Strength to 64 and 
enable Pan Noise Field. 
8. Click the Green + Button next to the Particle Update Stage and select Add 
Gravity Force Module from the Menu. Set Noise Strength to 64 and enable 
Pan Noise Field. 
9. Click the Green + Button next to the Particle Update Stage and select Add 
Color Module from the Menu. Using the Upper Gradient track, add 3 color 
values using the list below. 
a. Point 1, V = 0, R =0, G = 1.21, and B = 15.0 
b. Point 2, V = 0.5, R = 15.0, G = 0, and B = 15.0 
c. Point 3, V = 1, R =1, G = 1, and B = 1 
10. Click the Orange + Stage Button at the top of the Emitter Stage Stack and 
select Event Handler. 
11. Select the Event Handler Properties Module. Change the Execution 
Module to Spawned Particles. Set the Spawn Number to 5. 
12. Click the Green + Button next to the Event Handler Stage and select the 
Add Receive Location Event Module from the Menu. Change the Velocity 
Parameter to Apply.

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

