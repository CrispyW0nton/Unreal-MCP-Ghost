# Book Knowledge: Gameplay Framework

> Extracted from 3 books. Total 15 relevant sections.

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

### Creating the BP_EnemySpawner blueprint  (Page 294)

Spawning more enemies during gameplay 275
From now on, when the player shoots an enemy three times, the enemy will explode and 
be destroyed in a similar way to how the cylinder targets behaved.
Now that we can destroy enemies, we need to ramp up the difficulty for the player again 
by spawning more enemies.
Spawning more enemies during gameplay
We are going to spawn new enemies in the level periodically so that the game can 
continue if the player destroys the first few enemies, and if they are too slow to defeat 
enemies, then the difficulty will gradually increase.
Creating the BP_EnemySpawner blueprint 
We will create a blueprint that will spawn enemies in random locations in the level. The 
time between spawns is determined by a variable called SpawnTime. There is another 
variable called MaxEnemies that limits the spawning of enemies.
Follow these steps to create the blueprint:
1. In the content browser, access the Content > FirstPersonBP > Enemy 
folder. Click the Add button and choose the Blueprint Class option.
2. On the next screen, choose Actor as the parent class. Name the blueprint 
BP_EnemySpawner and double-click it to open the Blueprint Editor.
3. In the Variables category of the My Blueprint panel, click the + button to add 
a variable, and name it SpawnTime. In the Details panel, change Variable Type 
to Float, and check the Instance Editable attribute. Compile the blueprint and set 
DEFAULT VALUE to 10.0:
Figure 10.24 – Creating the SpawnTime float variable

---

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

### Character (Page 80)

Exploring the other Gameplay Framework classes 61
Some parameters show that the Pawn class can use the rotation values of the Controller 
class that is possessing it. Others parameters indicate how the Pawn class must be 
possessed by the Controller class.
The two main child classes of Pawn are Character and WheeledVehicle.
Character
The Character class is a child class of the Pawn class; therefore, an instance of the 
Character class can also be possessed by an instance of a Controller class. This class was 
created to represent characters that can walk, run, jump, swim, and fly.
A Blueprint based on the Character class would inherit the following character-specific 
Components:
• CapsuleComponent: This is used for collision testing.
• ArrowComponent: This indicates the current direction of the character.
• Mesh: This Component is a Skeletal Mesh that visually represents the character. 
The animation of the Mesh Component is controlled by an animation Blueprint.
• CharacterMovement: This Component is used to define various types of character 
movements, such as walking, running, jumping, swimming, and flying.
These Components are shown in the following screenshot:
Figure 3.26 – Character Class Components

---

### Array (Page 353)

334 Data Structures and Flow Control
3. Drag BP_RandomSpawner from the Content Browser and drop it on the level. 
The TargetPoints and Spawn Class variables appear in the Details panel of the 
instance because we checked the Instance Editable attribute. Click on the + icon 
to add elements to the array. Expand the drop-down menu of each element and 
select one of the TargetPoint instances that are in the level. In Spawn Class, select 
Blueprint_Effect_Smoke:
Figure 13.16 – Setting the variables of the BP_RandomSpawner instance
4. Click on the Play button of the Level Editor. BP_RandomSpawner will spawn an 
instance of Blueprint Effect Smoke at one of the TargetPoint instances. Exit and 
play again to see Blueprint Effect Smoke spawning in different locations:
Figure 13.17 – The instance of Blueprint Effect Smoke spawned on the level
Arrays are widely used in game development. Now, let's look at other types of containers.

---

## Source: Game Development with Unreal Engine 5 Volume 1 (Tiow Wee Tan)

### Procedural Generate Large Rocks (Page 171)

159
 
a. Settings Panel: The panel shows settings related to the “Density Filter” 
or “Static Mesh Spawner” node. The range of bound value (0.9–1.0) 
corresponds to a limit or threshold value that is being set for the procedural 
system. This might define a cap on the maximum number of objects to be 
spawned or a minimum required density for spawning to occur.
 3. Static Mesh Spawner Node: The “Static Mesh Spawner” node is 
where the actual instantiation of the static meshes occurs, based 
on the filtered density values. This node controls the spawning of 
3D objects onto the terrain, placing them where they are needed 
according to the procedural rules defined in the graph.
These nodes work together to dictate where and how often certain objects appear 
within a game environment, based on terrain data and specified rules. The final part of 
the connection solidifies the procedural logic, culminating in the placement of static 
meshes to enhance the game’s visual complexity and realism.
Figure 4-60.  The density value for this large rock sampler
4-61
 1. Static Mesh Assignment: The “Static Mesh” field is where we select 
the specific mesh that will be procedurally placed in the scene. In 
this case, we use a static mesh named “S_ForestRock_Formation_
vqauv” to be used by the spawner.
 2. Mobility Setting: The “Mobility” setting determines whether the 
spawned meshes are static, stationary, or movable. We set the 
“Mobility” option to “Static,” meaning the instances of this mesh 
will not be expected to move or change in game, which can be 
beneficial for performance.
Chapter 4 Revitalizing Visuals: Asset Import and Procedural Creation

---

## Source: Mastering Technical Art in Unreal Engine (Greg Penninck)

### The Orbiting Emitter (Page 158)

139 
Creating the Energy Orb 
Now that we have created our Energy Orb System and preview it in the level we can 
move onto further detailing the effect. We’ll learn about why additional emitters are 
often needed and push our creativity with Niagara further. 
The Orbiting Emitter 
We have created the focal point of our effect, however, VFX look more impressive and 
cooler when layered. By this we mean that the effect either has additional emitters, 
meshes or materials that help to add more visual interest to our work. We’ll now look 
at how we can do that for our cool Energy Orb. 
Our next part of the process will be to create the Orbiting Particles, these particles 
will quickly rotate around the storm in the center to add some additional visual inter­
est. We’ll do this by using location nodes to spawn the particles differently and then 
add velocity to move the particles. To take the effect further you may want to experi­
ment with some of the Dynamic Parameters or Color fading from the previous chapter. 
Let’s start building the Orbiting Emitter: 
1. In the Content Browser, navigate to the Content | VFX folder. 
2. Right click anywhere in the VFX Folder and create a FX\Niagara Emitter 
asset. From the pop up menu set the Template to be Empty and label the 
asset OrbitParticle_Emitter. 
3. Select the EmitterState module in the EmitterUpdate stage, change the 
parameter LeftCycle to Self. Then set the Loop Duration to 4. 
4. Now click the Orange + Button in the EmitterUpdate stage and create a 
Spawn Rate module. 
5. Select the Spawn Rate module and set the SpawnRate Parameter to 15. 
6. Select the Initialize Particle Module. Change the LifeTime parameter to a 
Random Float in Range using the dropdown arrow. Set the Minimum value 
to 3 and the Maximum Value to 4. 
7. Now set the SpriteSizeMode to be Random Uniform. Set the Uniform 
Sprite Size Min to be 0.1 and the Uniform Sprite Size Max to be 0.3. 
These particles will be quite small so expect to zoom in a fair bit to keep 
track of them. 
8. Click the Green + Button next to the Particle Spawn stage. Select Shape 
Location from the menu. The Shape Location node allows us to create parti­
cles based on a primitive shape. This can be helpful when we want to spread 
particles out and stop them from spawning at 0,0,0. 
9. Select the Shape Location module. Change the Shape Primitive to Ring / 
Disc. Set the Ring Radius to 3. You should now start to see the particles 
appear in a Ring formation, you will likely need to zoom into the Niagara 
Viewport to see this. 
The problem with this approach so far is that the particles are spawned randomly 
around the ring, if we want to animate them to create a follow effect, we need them to 
spawn more orderly. Let’s set that up!

---

### The Cauldron Sizzle Emitter (Page 171)

152 
Mastering Technical Art in Unreal Engine 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
7. Select the Initialize Particle Module. Set the Lifetime Min to 0.4 and the 
Lifetime Max to 2. You may wish to lower the Lifetime Max a bit more if 
the particles stay in the scene a bit too long. 
8. Change the Mass Mode Parameter to Unset. We don’t need to use this in 
the effect. Sometimes you may fnd some Modules or parameters can be 
removed or unset if variation isn’t required. 
9. Change the Sprite Size to Random Uniform. Set the Uniform Sprite Size 
Min to 0.1 and the Uniform Sprite Size Max to 0.25. 
10. A lot of the values in this emitter are very small as the particles will be 
very small on screen, our next task is to lower the velocities. Select the Add 
Velocity Module. Set the Velocity Speed Minimum to 4 and the Velocity 
Speed Maximum to 9. Change the Cone Axis to be X = 0, Y = 0, and Z = 1. 
Lastly set the Velocity Cone Angle to 65. 
11. Remove or disable the Gravity Module. 
12. Select the Drag Module, press the Reset Arrow to change the default value 
to 1. 
13. Remove or disable the Scale Color Module. 
14. Remove or disable the Scale Sprite Size by Speed Module. 
15. Click the Green + Button next to Particle Update and select the Vortex 
Force Module. 
16. Select the Vortex Force Module and set Vortex Force Amount to 35 and 
Origin Pull Amount to 55. As these particles could spawn anywhere in 
the world, we also need to change the Vortex Origin, the default value will 
always put the Vortex Origin in the wrong place. Click the Down arrow to 
the right of Simulation Position and search for Particles Initial Position. 
This will put the Vortex wherever the Sizzle Particles spawn. 
17. Click the Green + Button next to Particle Update and select the Color 
Module. 
18. Select the Color Module, change the Color to Color from Curve. Then set 
the frst color value on the gradient to be R = 213, G = 500, and B = 0. Then 
add another box half‑way along the upper track and set the values to be 
R = 0.47, G = 1, and B = 0. This will create a very bright fash when the par­
ticles spawn. 
19. Next we need to add in some functionality to read in the Collision Event 
from our sparks. To do this click the Orange + Stage button at the top of the 
CauldronSizzleEmitter and pick Event Handler from the menu. 
20. You’ll now see the Event Handler Stage added above our Renderer Stage. 
21. Select the Event Handler Source, change the Execution Mode to Spawned 
Particles and Set the Spawn Number to 10. You can also use the Random 
Spawn Boolean Checkbox to add variation here. This will control how 
many particles spawn when our Sparks particles Collide. Be careful as it’s 
easy to spawn several thousand particles here by mistake. 
22. Click the Green + Button next to the Event Handler Stage and select the 
Receive Collision Event Module.

---

### Answers (Page 175)

156 
Mastering Technical Art in Unreal Engine 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
Question 2: What Module should we use if we want to adjust a Sprite Particles Size 
by Speed? 
a. Transform Sprite Size by Speed 
b. Scale Sprite Size by Force 
c. Scale Sprite Size by Speed 
d. Press E while in the Niagara System Editor. 
e. All of the above. 
Question 3: When adding variation to Particle Color what option provides us with 
a nice Gradient to animate Color and Alpha? 
a. Color Over Time. 
b. Color From Curve. 
c. Color. 
Question 4: What is the Difference between Spawn Rate and Spawn Instantaneous. 
a. Spawn Rate will create a number of particles continuously whereas 
Spawn Instantaneous will destroy particles. 
b. Spawn Rate will create a number of particles at the Beginning of an 
Emitters Life whereas Spawn Instantaneous will create Particles at the 
end of an Emitters Life. 
c. Spawn Rate will create a number of particles continuously whereas 
Spawn Instantaneous will create a number of particles at a precise 
moment. 
Answers 
Question 1: a 
Question 2: c 
Question 3: b 
Question 4: c

---

## Source: Game Development with Unreal Engine 5 Volume 1 (Tiow Wee Tan)

### Static Mesh Spawner (Page 164)

152
Static Mesh Spawner
4-54
When multiple mesh entries are present, the node randomly chooses one asset 
from the array for each point (or the randomness can also be based on the weight of 
individual assets). This selected asset is then spawned at the designated point’s position, 
orientation, and scale. Various parameters within the node offer control over spawning 
behavior, including options for random rotation, random scale, alignment mode, and 
collision mode.
The Static Mesh Spawner node is particularly valuable for constructing intricate 
scenes that encompass diverse variations of static meshes, such as structures, boulders, 
vegetation, or objects.
Optimization is key in certain situations, and in the individual mesh entries, we 
have the flexibility to modify collision modes, enabling options like no collision or 
shadows for very small spawned meshes. We can further control the rendering 
distance (culling) for these meshes, ensuring that only nearby objects are rendered. 
This optimization significantly improves gameplay performance and efficient 
resource usage.
Here are the steps and descriptions that we can follow to add new static mesh into 
this Static Mesh Spawner:
 1. Mesh Entries Setup: As shown in Step 1, we can add additional 
“Mesh Entries” elements, where we can define the array of static 
meshes to spawn. Each index within this array corresponds to a 
different mesh that can be procedurally placed in the scene as 
shown in Step 2.
Chapter 4 Revitalizing Visuals: Asset Import and Procedural Creation

---

## Source: Blueprints Visual Scripting for Unreal Engine 5 (Marcos Romero)

### Giving the enemy sight with PawnSensing (Page 267)

248 Building Smart Enemies with Artificial Intelligence
4. In the Details panel of the PawnSensing component, look in the Events category 
and click the green button of the On See Pawn event to add it to the EventGraph:
Figure 9.45 – Adding the On See Pawn event
5. The On See Pawn event triggers when the enemy sees an instance of the Pawn class 
(or its child class, Character) along its line of sight. We need to check whether the 
instance seen is the player (the FirstPersonCharacter class). If it is the player, then 
we store the instance reference in the Blackboard: 
Figure 9.46 – Storing the PlayerCharacter reference in the Blackboard
6. Drag a wire from the Pawn output pin of the On See Pawn event and add a Cast 
To FirstPersonCharacter node.
7. Right-click on the graph and add a Get Blackboard node.
8. Drag a wire from the Return Value pin of Get Blackboard and add a Set Value as 
Object node.
9. Drag a wire from the Key Name pin of the Set Value as Object node and add 
a GET Player Key Name node.
10. Drag a wire from the Object Value pin of the Set Value as Object node and 
connect to the As First Person Character output pin.
11. Connect the white execution pins of the Cast To FirstPersonCharacter and Set 
Value as Object nodes. Compile the Blueprint.

---

### Creating the BP_EnemySpawner blueprint  (Page 295)

276 Upgrading the AI Enemies
4. Create another variable in the My Blueprint panel and name it MaxEnemies. 
In the Details panel, change Variable Type to Integer, and check the Instance 
Editable attribute. Compile the blueprint and set DEFAULT VALUE to 5:
Figure 10.25 – Creating the MaxEnemies integer variable
5. In the My Blueprint panel, click the + button in the Macros category to create 
a macro. Change the name of the macro to SpawnEnemy.
6. In the Details panel of the macro, create an input parameter named In and an 
output parameter named Out both of the Exec type:
7. On the tab created for the SpawnEnemy macro, add these nodes to spawn 
a BP_EnemyCharacter instance in a random location in the level:
Figure 10.26 – The SpawnEnemy macro
8. Right-click on the graph and add a Spawn AIFrom Class node. Connect the white 
execution pins of the Inputs, Spawn AIFrom Class, and Outputs nodes.

---

### Adding noise to the player's actions (Page 289)

270 Upgrading the AI Enemies
Now that we have modified our enemy AI to be able to detect sounds that are broadcast to 
the listener, we need to create the nodes in the FirstPersonCharacter blueprint that 
will trigger the hearing response and attach them to player actions.
Adding noise to the player's actions
The Pawn Sensing component of EnemyController is only able to detect noise if it is 
created from Pawn Noise Emitter. The existing sound effect that we play when the player 
fires their gun will not trigger the enemy's Pawn Sensing component. It is important to 
know that the nodes that produce noise for pawn sensing have no direct relationship with 
the sound a player hears. The noise exists only in terms of producing an event that the AI 
can hear and respond to.
The Pawn Noise Emitter component must be added to an actor for the noises it 
broadcasts to be detected by a pawn sensor. We will change two player abilities, namely 
sprinting and shooting, to produce detectable noise by utilizing this component.
These are the steps to use Pawn Noise Emitter:
1. In the content browser, access the Content > FirstPersonBP > 
Blueprints folder and double-click on the FirstPersonCharacter 
Blueprint.
2. In the Components panel, click the Add button and search for pawn. Select the 
Pawn Noise Emitter component:
Figure 10.17 – Adding the Pawn Noise Emitter component
3. We will begin by adding noise to sprinting. In the My Blueprint panel, double-click 
the ManageStaminaDrain macro to open the macro tab. We will add the Make 
Noise node after the SET Player Stamina node:

---

### Array (Page 349)

330 Data Structures and Flow Control
Let's create an example to examine the use of arrays that store object references.
Array example – creating BP_RandomSpawner
In this example, we'll create a Blueprint called BP_RandomSpawner, which will have 
an array of Target Points. The elements of the Target Points array can be set in the Level 
Editor. When the level starts, the BP_RandomSpawner Blueprint will randomly select 
one element of Target Points and spawn an instance of a specified Actor class in the same 
location of the Target Point selected.
These are the steps to create this example:
1. Create a project based on the Third Person template with the starter content.
2. In the Content Browser, access the Content folder. Right-click in the empty 
space next to the list of folders and select the New Folder option. Name the folder 
BookUE5. We will use this folder to store this chapter's assets.
3. Open the BookUE5 folder you just made, then click the Add button in the Content 
Browser, and choose the Blueprint Class option. 
4. On the next screen, choose Actor as the parent class. Name the Blueprint 
BP_RandomSpawner and double-click it to open the Blueprint Editor.
5. In the My Blueprint panel, create a new variable named TargetPoints. In the 
Details panel, click the Variable Type drop-down menu and search for target 
point. Hover over Target Point to display a submenu and then choose Object 
Reference. Click the icon to the right of Variable Type and select the Array icon. 
Check the Instance Editable attribute, as shown in the following screenshot:
Figure 13.10 – Creating an array of Target Point
6. Create another variable and name it SpawnClass. Click the Variable Type 
drop-down menu and search for actor. Hover over Actor to display a submenu 
and then choose Class Reference:

---

### Array (Page 350)

Exploring different types of containers 331
Figure 13.11 – Creating a variable that references an Actor class
7. Click the icon to the right of Variable Type and select the single variable icon. 
Check the Instance Editable attribute. We will use the class specified in the 
SpawnClass variable when spawning an Actor:
Figure 13.12 – SpawnClass can be specified in an instance on the level
In Event BeginPlay, we will use a Branch node to validate the Spawn Class and 
Target Points variables. Any variable storing a reference should be validated before 
use to avoid runtime errors. If the variables are valid, then we spawn an Actor 
using the class stored in the Spawn Class variable and the transform of a randomly 
selected Target Point stored in the array:
Figure 13.13 – The Event BeginPlay actions

---

