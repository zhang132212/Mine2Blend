/* Build-only extraction of model geometry from the user's installed Minecraft.
 * Generated game data remains separately licensed; no game classes are bundled.
 */
import java.nio.file.*;
import java.util.*;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonParser;
import com.google.gson.JsonArray;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.tags.TagKey;
import net.minecraft.tags.TagLoader;
import java.util.jar.JarFile;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.client.model.geom.LayerDefinitions;
import org.joml.Vector3f;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.Direction;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.EmptyBlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.FenceBlock;
import net.minecraft.world.level.block.IronBarsBlock;
import net.minecraft.world.level.block.WallBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.SupportType;
import net.minecraft.commands.arguments.blocks.BlockStateParser;
import net.minecraft.world.phys.shapes.VoxelShape;
import net.minecraft.tags.BlockTags;

public class DumpGameModels {
    private static Set<String> resolveTag(String name,Map<String,JsonArray> raw,Map<String,Set<String>> resolved,Set<String> chain) {
        if (resolved.containsKey(name)) return resolved.get(name);
        if (!chain.add(name)) throw new IllegalStateException("Cyclic block tag: "+name);
        Set<String> values=new LinkedHashSet<>();
        for (var value:raw.getOrDefault(name,new JsonArray())) {
            String id=value.isJsonPrimitive()?value.getAsString():value.getAsJsonObject().get("id").getAsString();
            if (id.startsWith("#")) values.addAll(resolveTag(id.substring(1),raw,resolved,new HashSet<>(chain)));
            else values.add(id);
        }
        resolved.put(name,values);return values;
    }
    private static void bindBlockTags() throws Exception {
        Map<String,JsonArray> raw=new TreeMap<>();
        var location=Path.of(SharedConstants.class.getProtectionDomain().getCodeSource().getLocation().toURI());
        try (var jar=new JarFile(location.toFile())) {
            var entries=jar.entries();String prefix="data/minecraft/tags/block/";
            while(entries.hasMoreElements()) {
                var entry=entries.nextElement();String path=entry.getName();
                if(path.startsWith(prefix)&&path.endsWith(".json")) {
                    String name="minecraft:"+path.substring(prefix.length(),path.length()-5);
                    raw.put(name,JsonParser.parseString(new String(jar.getInputStream(entry).readAllBytes(),java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject().getAsJsonArray("values"));
                }
            }
        }
        Map<String,Set<String>> resolved=new HashMap<>();
        Map<TagKey<Block>,List<Holder<Block>>> tags=new HashMap<>();
        for(String name:raw.keySet()) {
            List<Holder<Block>> holders=new ArrayList<>();
            for(String id:resolveTag(name,raw,resolved,new HashSet<>())) holders.add(BuiltInRegistries.BLOCK.get(Identifier.parse(id)).orElseThrow());
            tags.put(TagKey.create(Registries.BLOCK,Identifier.parse(name)),holders);
        }
        BuiltInRegistries.BLOCK.prepareTagReload(new TagLoader.LoadResult<>(Registries.BLOCK,tags)).apply();
    }
    public static void main(String[] args) throws Exception {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
        bindBlockTags();
        Map<String,Object> layers = new TreeMap<>();
        Map<String,Integer> skipped = new TreeMap<>();
        for (var entry : LayerDefinitions.createRoots().entrySet()) {
            List<Object> quads = new ArrayList<>();
            entry.getValue().bakeRoot().visit(new PoseStack(), (pose, part, index, cube) -> {
                for (var polygon : cube.polygons) {
                    boolean valid=true;
                    List<Object> positions = new ArrayList<>();
                    List<Object> uv = new ArrayList<>();
                    for (var vertex : polygon.vertices()) {
                        Vector3f p = pose.pose().transformPosition(vertex.worldX(), vertex.worldY(), vertex.worldZ(), new Vector3f());
                        if (!Float.isFinite(p.x) || !Float.isFinite(p.y) || !Float.isFinite(p.z) || !Float.isFinite(vertex.u()) || !Float.isFinite(vertex.v())) valid=false;
                        positions.add(List.of(-p.x, 1.5f-p.y, p.z));
                        uv.add(List.of(vertex.u()*16, vertex.v()*16));
                    }
                    if (valid) quads.add(List.of(positions,uv,part));
                    else skipped.merge(entry.getKey().toString(),1,Integer::sum);
                }
            });
            layers.put(entry.getKey().toString(),quads);
        }
        var data=Map.of("game_version","26.2","layers",layers,"nonfinite_quads_skipped",skipped);
        Files.writeString(Path.of(args[0]),new GsonBuilder().create().toJson(data));
        System.out.println("VANILLA_MODEL_LAYERS_OK "+layers.size());
        List<Object> palette = new ArrayList<>();
        Map<Object,Integer> lookup = new HashMap<>();
        Map<String,Integer> states = new TreeMap<>();
        var wallConnect=WallBlock.class.getDeclaredMethod("connectsTo",BlockState.class,boolean.class,Direction.class);
        wallConnect.setAccessible(true);
        var wallCovered=WallBlock.class.getDeclaredMethod("isCovered",VoxelShape.class,VoxelShape.class);wallCovered.setAccessible(true);
        var postField=WallBlock.class.getDeclaredField("TEST_SHAPE_POST");postField.setAccessible(true);
        var sidesField=WallBlock.class.getDeclaredField("TEST_SHAPES_WALL");sidesField.setAccessible(true);
        VoxelShape postShape=(VoxelShape)postField.get(null);
        @SuppressWarnings("unchecked") Map<Direction,VoxelShape> wallShapes=(Map<Direction,VoxelShape>)sidesField.get(null);
        for (var block : BuiltInRegistries.BLOCK) for (var state : block.getStateDefinition().getPossibleStates()) {
            Map<String,Object> faces = new TreeMap<>();
            Map<String,Object> sturdy = new TreeMap<>();
            Map<String,Object> connections = new TreeMap<>();
            for (var direction : Direction.values()) {
                List<Object> boxes = new ArrayList<>();
                for (var box : state.getFaceOcclusionShape(direction).toAabbs()) boxes.add(List.of(box.minX,box.minY,box.minZ,box.maxX,box.maxY,box.maxZ));
                faces.put(direction.getName(),boxes);
                sturdy.put(direction.getName(),List.of(
                    state.isFaceSturdy(EmptyBlockGetter.INSTANCE,BlockPos.ZERO,direction,SupportType.FULL),
                    state.isFaceSturdy(EmptyBlockGetter.INSTANCE,BlockPos.ZERO,direction,SupportType.CENTER),
                    state.isFaceSturdy(EmptyBlockGetter.INSTANCE,BlockPos.ZERO,direction,SupportType.RIGID)));
                boolean face=state.isFaceSturdy(EmptyBlockGetter.INSTANCE,BlockPos.ZERO,direction.getOpposite());
                if (direction.getAxis().isHorizontal()) connections.put(direction.getName(),List.of(
                    ((FenceBlock)Blocks.OAK_FENCE).connectsTo(state,face,direction),
                    ((FenceBlock)Blocks.NETHER_BRICK_FENCE).connectsTo(state,face,direction),
                    ((IronBarsBlock)Blocks.IRON_BARS).attachsTo(state,face),
                    (boolean)wallConnect.invoke(Blocks.COBBLESTONE_WALL,state,face,direction)));
            }
            VoxelShape bottom=state.getCollisionShape(EmptyBlockGetter.INSTANCE,BlockPos.ZERO).getFaceShape(Direction.DOWN);
            Map<String,Object> wallAbove=new TreeMap<>();
            wallAbove.put("wall_post",block instanceof WallBlock && state.getValue(WallBlock.UP));
            wallAbove.put("post_override",state.is(BlockTags.WALL_POST_OVERRIDE));
            wallAbove.put("post_covered",wallCovered.invoke(null,bottom,postShape));
            for(var entry:wallShapes.entrySet()) wallAbove.put(entry.getKey().getName(),wallCovered.invoke(null,bottom,entry.getValue()));
            var properties=Map.of("solid_render",state.isSolidRender(),"can_occlude",state.canOcclude(),"solid",state.isSolid(),
                "connection_exception",Block.isExceptionForConnection(state),"faces",faces,"sturdy",sturdy,"connections",connections,"wall_above",wallAbove);
            Integer index=lookup.get(properties);
            if (index==null) { index=palette.size();palette.add(properties);lookup.put(properties,index); }
            states.put(BlockStateParser.serialize(state),index);
        }
        Files.writeString(Path.of(args[0]).resolveSibling("vanilla-block-physics.json"),new GsonBuilder().create().toJson(Map.of("game_version","26.2","palette",palette,"states",states)));
        System.out.println("VANILLA_BLOCK_PHYSICS_OK "+states.size()+" states / "+palette.size()+" shapes");
    }
}
