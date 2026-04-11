# Book Knowledge: AI & Behavior Trees

> Extracted from 1 books. Total 15 relevant sections.

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

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

### Overlapping a patrol point (Page 258)

Creating navigation behavior 239
Figure 9.32 – The UpdatePatrolPointBB macro
4. Right-click on the graph and add a Get Blackboard node. This is a utility function 
that searches for the Blackboard being used by the AI controller.
5. Drag a wire from the Return Value pin of Get Blackboard and add a Set Value as 
Object node.
6. Drag a wire from the Key Name pin of the Set Value as Object node and add 
a GET Patrol Point Key Name node.
7. Drag a wire from the Object Value pin of the Set Value as Object node and add 
a GET Current Patrol Point node.
8. Connect the white execution pins of the Inputs, Set Value as Object, and Outputs 
nodes. Compile the Blueprint.
Next, we need to check when a BP_EnemyCharacter instance overlaps with a patrol 
point to update the CurrentPatrolPoint key of BB_EnemyBlackboard.
Overlapping a patrol point
We will use Event ActorBeginOverlap to verify when an instance of BP_
EnemyCharacter reaches one of its two patrol points, and then we swap the patrol 
point that the instance is moving toward. Every time we update the CurrentPatrolPoint 
variable, we need to call the UpdatePatrolPointBB macro.
In Event BeginPlay, we will set an initial patrol point to CurrentPatrolPoint and call the 
UpdatePatrolPointBB macro.
Follow these steps to create the events:
1. In the EventGraph of BP_EnemyCharacter, drag a wire from the white execution 
pin of Event BeginPlay and add a SET Current Patrol Point node.
2. Drag a wire from the input pin of SET Current Patrol Point and add a GET Patrol 
Point 1 node.

---

### Giving the enemy sight with PawnSensing (Page 266)

Making the AI chase the player 247
You should see the red enemy character start navigating to the first of the two patrol 
points. When it reaches the first point, it will briefly pause and then start walking to the 
second patrol point. This pattern will continue back and forth while the game is running.
Now that we have a patrol behavior established, we will give the enemy the ability to see 
the player and pursue them.
Making the AI chase the player
There is a component named PawnSensing that can be used to add vision and hearing 
to the enemy. We will use this component and expand our Behavior Tree to make the 
enemy pose some threat to the player. 
Giving the enemy sight with PawnSensing
To grant the enemy the ability to detect the player, we need to add the PawnSensing 
component to BP_EnemyController and store the PlayerCharacter reference in 
BB_EnemyBlackboard when the enemy sees the player.
These are the steps to use the PawnSensing component:
1. Open the BP_EnemyController Blueprint.
2. Create a variable in the My Blueprint panel. In the Details panel, name the variable 
PlayerKeyName and change Variable Type to Name. Compile the Blueprint and 
set Default Value to PlayerCharacter.
3. In the Components panel, click the Add button and search for pawn. Select the 
Pawn Sensing component:
Figure 9.44 – Adding the Pawn Sensing component

---

### Adding hearing to the Behavior Tree (Page 282)

Making enemies hear and investigate sounds 263
Making enemies hear and investigate sounds
Enemies that can only pursue players who walk directly in front of them can easily be 
avoided. To address this, we will take advantage of the PawnSensing component to have 
the enemy detect nearby sounds that the player makes. If the player makes a sound within 
the detection range of an enemy, then the enemy will walk to the location of that sound 
to investigate. If they catch the player in their sight, they will try to attack; otherwise, they 
will wait at the location of the sound for a moment before returning to their patrol.
Adding hearing to the Behavior Tree
We will add a sequence of tasks that occur when the enemy hears a sound. We want the 
enemy to continue attacking the player once they see them, so investigating a sound has 
a lower priority on the Behavior Tree.
To have the enemy investigate the point where it heard a sound, we will need to create two 
keys within the blackboard. The HasHeardSound key is of the Boolean type and will 
be used to store whether a sound has been heard. The LocationOfSound key is of the 
Vector type and will be used to store the location that the sound came from – hence, the 
location that the enemy AI should investigate.
Follow these steps to create the blackboard keys and add the Investigate Sound sequence 
node to the Behavior Tree:
1. In the content browser, access the Content/FirstPersonBP/Enemy folder and 
double-click on the BT_EnemyBehavior asset to open the Behavior Tree Editor.
2. Click the Blackboard tab:
Figure 10.7 – Switching the Behavior Tree Editor to Blackboard mode
3. Click the New Key button and select Bool as the key type. Name this new key 
HasHeardSound:
Figure 10.8 – The HasHeardSound Bool key

---

### Identifying a wander point with a custom task (Page 297)

278 Upgrading the AI Enemies
19. Drag a wire from the output pin of the Length node and add a Less node. Connect 
the output pin of the Less node to the Condition parameter of the Branch node.
20. Drag a wire from the bottom pin of the Less node and add a Get Max Enemies 
node.
21. Compile, save, and close the Blueprint Editor. Drag BP_EnemySpawner from 
the content browser and drop anywhere on the level to create an instance. Click the 
Play button to test your enemy spawning.
You will regularly see new enemies appear as you run the game. Note, however, that the 
enemies are not moving once spawned unless they hear or see the player. This is because 
they are not being created with an established patrol point to pursue. Rather than adding 
patrol points to our spawned enemies, we will add randomness to our enemy navigation 
behavior.
Creating enemy wandering behavior
In Chapter 9, Building Smart Enemies with Artificial Intelligence, we set the default 
behavior for enemies as a patrolling movement between two points. While this worked 
well as a testbed for our hearing and seeing components and would be appropriate for 
a stealth-oriented game, we are going to ramp up the challenge and action of this game's 
experience by replacing this behavior with random wandering. This will make avoiding 
enemies significantly harder, encouraging more direct confrontations. To do this, we are 
going to return to the BT_EnemyBehavior Behavior Tree. 
Identifying a wander point with a custom task
We need to create a key in BB_EnemyBlackboard that will store the location of the next 
destination that the enemy should wander to. Unlike the PatrolPoint key, our destination 
won't be represented by an in-game actor but, rather, by vector coordinates. Then, we will 
create a task to determine where in the level the enemy should be wandering.
Follow these steps to create the key and the task:
1. In the content browser, double-click the BT_EnemyBehavior asset to open the 
Behavior Tree Editor.
2. Click the Blackboard tab to edit BB_EnemyBlackboard.
3. Click the New Key button and select Vector as the key type. Name this new key 
WanderPoint:

---

### Table of Contents (Page 9)

viii Table of Contents
8
Creating Constraints and Gameplay Objectives
Constraining player actions 
 180
Draining and regenerating stamina 
 181
Preventing firing actions when 
out of ammo 
 195
Creating collectible objects 
 196
Setting a gameplay 
win condition 
 201
Displaying a target goal in the HUD 
 202
Creating a win menu screen 
 204
Displaying the WinMenu 
 210
Triggering a win 
 212
Summary 
 214
Quiz 
 215
Part 3: Enhancing the Game
9
Building Smart Enemies with Artificial Intelligence
Setting up the enemy actor to 
navigate 
 220
Importing from the Marketplace 
 220
Expanding the play area 
 221
Making the level traversable with a 
NavMesh asset 
 227
Creating the AI assets 
 229
Setting up the BP_EnemyCharacter 
Blueprint 
 231
Creating navigation behavior   233
Setting up patrol points 
 233
Creating the Blackboard keys 
 234
Creating the variables in BP_
EnemyCharacter 
 236
Updating the current patrol point key   237
Overlapping a patrol point 
 239
Running the Behavior Tree in 
the AI Controller 
 241
Teaching our AI to walk with the 
Behavior Tree 
 242
Selecting the patrol points in the 
BP_EnemyCharacter instance 
 246
Making the AI chase the player  247
Giving the enemy sight with 
PawnSensing 
 247
Creating a Behavior Tree Task 
 249
Adding conditions to the Behavior Tree  251
Creating a chasing behavior 
 253
Summary 
 254
Quiz 
 255

---

### Creating the AI assets (Page 248)

Setting up the enemy actor to navigate 229
Figure 9.16 – Press the P key to toggle the NavMesh visibility on and off
With our play area and NavMesh now set up, we can return our focus to creating the 
enemy and its AI.
Creating the AI assets
We need to create assets of four types that will work together to manage the behavior of 
our enemy:
• Character: A blueprint class that represents the enemy character in the level.
• AI Controller: A blueprint class that serves as a connection between the character 
and the Behavior Tree. It routes the information and actions that are generated 
within the Behavior Tree to the character, which will enact those actions.
• Behavior Tree: A Behavior Tree is the source of the decision-making logic that will 
instruct our enemy on what conditions should cause it to perform which actions.
• Blackboard: A Blackboard is a container for all the data used in the decision-
making that is shared between the AI controller and the Behavior Tree. 
These are the steps to create the four assets:
1. In the content browser, access the /Content/FirstPersonBP/ folder. Right-
click in the empty space next to the list of folders and select the New Folder option. 
Name the new folder Enemy.
2. Open the Enemy folder you created, and then right-click in the empty folder space 
and select Blueprint Class.

---

### Setting up the BP_EnemyCharacter Blueprint (Page 250)

Setting up the enemy actor to navigate 231
8. Rename the Behavior Tree asset BT_EnemyBehavior.
9. Finally, to create the Blackboard asset, right-click in the empty space of the 
Enemy folder, hover over Artificial Intelligence to display a submenu, and select 
Blackboard. Name it BB_EnemyBlackboard.
10. The following screenshot shows the assets of the Enemy folder:
Figure 9.19 – The Enemy folder assets
These are the assets that we will use to implement the AI of the enemy character. Next, we 
need to make some modifications to the BP_EnemyCharacter Blueprint.
Setting up the BP_EnemyCharacter Blueprint
As we created BP_EnemyCharacter as a Ue4ASP_Character child class, it inherited 
information about the desired mesh, texture, and animations from the character created 
for the animation pack we imported. Some of this information we want to keep, such 
as the mesh and animations. However, we need to ensure that BP_EnemyCharacter 
knows how to be controlled by the right AI Controller. We will also change the material of 
BP_EnemyCharacter and hide the capsule component that is being shown in the game.
Note
When you open a Blueprint that does not have any scripts, a simple editor is 
displayed to edit the default values only. You need to click on the Open Full 
Blueprint Editor link at the top to see the usual layout.

---

### Setting up patrol points (Page 252)

Creating navigation behavior 233
5. In the Components panel, click on CapsuleComponent (CollisionCylinder) 
(Inherited). In the Details panel, change Collision Presets to BlockAllDynamic, 
and in the RENDERING category, check the Hidden in Game property:
Figure 9.23 – Hiding CapsuleComponent
6. Compile the blueprint and drag the BP_EnemyCharacter blueprint onto the 
level to create an instance of the enemy in our play area.
In this section, we learned how to import assets from the Marketplace. We expanded the 
level and made it traversable using a NavMesh. We created the AI assets, and now we are 
ready to implement the navigation behavior of the enemy. 
Creating navigation behavior
The first goal for our enemy will be to get it to navigate between points that we create on 
the map. To accomplish this, we'll need to create points on the map that the enemy will 
navigate to, and then we need to set up the behavior that will cause the enemy to move to 
each of the points in a cycle.
Setting up patrol points
Let's start by creating the path we want the AI to patrol. We will use a Sphere Trigger to 
represent a patrol point, since it generates overlap events and is hidden in the game. We 
need at least two patrol points on the level, since each instance of BP_EnemyCharacter 
can navigate between two patrol points.

---

### Overlapping a patrol point (Page 259)

240 Building Smart Enemies with Artificial Intelligence
3. Drag a wire from the white output pin of the SET Current Patrol Point node and 
add the UpdatePatrolPointBB macro node:
Figure 9.33 – Setting an initial patrol point
4. Now, let's create the Event ActorBeginOverlap event, which swaps the patrol 
points. The event first checks whether the enemy overlaps with Patrol Point 1. If it 
is true, then the event sets Patrol Point 2 as Current Patrol Point. If it is false, 
then the event checks whether the enemy overlaps with Patrol Point 2. In this case, 
the event sets Patrol Point 1 as Current Patrol Point:
Figure 9.34 – Swapping the patrol points
5. The nodes of steps 5–8 are to check whether the enemy overlaps with Patrol Point 
1. Drag a wire from the white execution pin of the Event ActorBeginOverlap node 
and add a Branch node.
6. Drag a wire from the Condition input pin of the Branch node and add an Equal 
node.
7. Drag a wire from the top input pin of the Equal node and add a GET Patrol Point 1 
node.
8. Connect the bottom input pin of the Equal node to the Other Actor output pin of 
the Event ActorBeginOverlap node.

---

### Summary (Page 273)

254 Building Smart Enemies with Artificial Intelligence
3. Drag another wire from the Attack Player sequence node and add a BTTask_
ClearBBValue task node. In the Details panel, change Key to PlayerCharacter and 
change Node Name to Reset Player seen:
Figure 9.55 – Clearing the PlayerCharacter value in the Blackboard
4. Save the Behavior Tree and close the Behavior Tree Editor. Press the Play button 
in the Level Editor to test the enemy behavior.
As you navigate the player character in front of the patrolling enemy, the enemy will 
stop its patrol and chase the player. When the enemy reaches the player, it will stop for 
2 seconds before returning to its patrol path. If it re-establishes a line of sight with the 
player, then it will interrupt its patrol and begin chasing the player again.
Summary
In this chapter, we began the process of changing our simple moving targets into 
fleshed-out game enemies that can challenge the player. In the process, you learned the 
basics of how AIControllers, Behavior Trees, and Blackboards can be leveraged together to 
create an enemy with the ability to sense the world around it and make decisions based on 
that information.
As we continue the process of developing our AI to pose a serious challenge to the player, 
you can use the skills you have learned to consider other kinds of behaviors you might be 
able to give an enemy. Continued exploration of AI mechanics will see you continually 
coming back to the core loop of sensing, decision-making, and acting that we began 
implementing here.

---

### Teaching our AI to walk with the Behavior Tree (Page 261)

242 Building Smart Enemies with Artificial Intelligence
3. Set the BTAsset input parameter to BT_EnemyBehavior:
Figure 9.35 – Running the Behavior Tree
4. Compile and save the Blueprint.
We have completed the necessary actions in the Blueprints to navigate the patrol points. 
We can now move on to the heart of the AI – the Behavior Tree.
Teaching our AI to walk with the Behavior Tree
Behavior Tree is a tool used to model the behavior of characters. It has control flow nodes 
and task nodes.
The two primary control flow nodes you will utilize are Selector and Sequence. A 
Selector node runs each of the nodes connected underneath it – called its children – from 
left to right, but it succeeds and stops running as soon as one child successfully runs. Thus, 
if a Selector node has three children, then the only way the third child node will run is 
if the first two children failed to execute because the conditions attached to them were 
false. A Sequence node is just the opposite. It also runs all the children in a sequence 
from left to right, but the Sequence node only succeeds if all the children succeed. 
The first child to fail causes the whole sequence to fail, ending the execution and aborting 
the sequence.
Follow these steps to create our first Behavior Tree:
1. In the content browser, double-click the BT_EnemyBehavior asset to open the 
Behavior Tree Editor.
2. In the Details panel, click the BEHAVIORTREE category and select 
BB_EnemyBlackboard as Blackboard Asset. The KEYS dropdown of BB_
EnemyBlackboard will appear in the Blackboard panel at the bottom:

---

### Creating the Blackboard keys (Page 253)

234 Building Smart Enemies with Artificial Intelligence
Follow these steps to create the patrol points:
1. In the Level Editor, click the Create button located on the toolbar, and then click on 
Sphere Trigger. Place the Sphere Trigger anywhere on the floor: 
Figure 9.24 – Creating a Sphere Trigger
2. In the Details panel, rename the Sphere Trigger PatrolPoint1. 
3. Create another Sphere Trigger and name it PatrolPoint2. Place it far away from 
the first patrol point so that movement between the two points is noticeable.
With our patrol points established, we can move on to building the intelligence of 
our enemy.
Creating the Blackboard keys
A Blackboard stores information using keys and values. BB_EnemyBlackboard will 
have two keys, one for storing the current patrol point and another to store a reference to 
the player character. This information will be referenced by the Behavior Tree.
These are the steps to create the keys:
1. Open BB_EnemyBlackboard from the content browser.
2. Click on New Key and select Object as Key Type.

---

### Creating the variables in BP_EnemyCharacter (Page 255)

236 Building Smart Enemies with Artificial Intelligence
Now, we need to set the value of the CurrentPatrolPoint key within Blackboard to 
the actual patrol point in the level. We can do this from the BP_EnemyCharacter 
Blueprint.
Creating the variables in BP_EnemyCharacter
We will create variables in BP_EnemyCharacter to store the patrol points and the key 
names of the Blackboard. 
Follow these steps to create the variables:
1. Open the BP_EnemyCharacter Blueprint.
2. In the Variables category of the My Blueprint panel, click the + button to add 
a variable and name it PatrolPoint1. 
3. In the Details panel, click the Variable Type drop-down menu and search for 
Actor. Hover over Actor to display a submenu, and then choose Object Reference. 
Check the Instance Editable attribute:
Figure 9.27 – Creating a variable that references an Actor instance
4. Follow the same steps to create a second Actor variable called PatrolPoint2.
5. Create another Actor variable called CurrentPatrolPoint. This time, leave the 
Instance Editable attribute unchecked. 
6. These are the variables we created. The open eye icon means that the variable is 
Instance Editable, so the references of PatrolPoint1 and PatrolPoint2 variables 
will be set in the Level Editor:

---

### Selecting the patrol points in the BP_EnemyCharacter instance (Page 265)

246 Building Smart Enemies with Artificial Intelligence
Note
Note the small gray circles with numbers inside of them that are positioned 
at the upper-right corner of the nodes. These indicate the execution order of 
the nodes, which are ordered according to their left-to-right and top-to-down 
positions. The first node to be evaluated will be labeled with a 0 badge.
Now, we have everything set up to test the enemy patrol.
Selecting the patrol points in the BP_EnemyCharacter 
instance
We created the PatrolPoint1 and PatrolPoint2 variables as Instance Editable in 
BP_EnemyCharacter to be able to set them in the Level Editor.
These are the steps to selecting the patrol points:
1. In the Level Editor, select the instance of BP_EnemyCharacter that we placed on 
the level.
2. In the Details panel, navigate down to the Default category and set Patrol Point 1 
to the PatrolPoint1 instance and Patrol Point 2 to the PatrolPoint2 instance:
Figure 9.43 – Selecting the patrol points
3. Save the level and click the Play button to test.

---

