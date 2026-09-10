package jp.km.ripperdoc;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public final class RipperdocConfig {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final Path PATH = FabricLoader.getInstance().getConfigDir().resolve("ripperdoc-server.json");

    public int zandeSpeedPercent = 50;
    public double berserkAttack = 6.0;
    public int berserkMiningPercent = 60;
    public boolean migratedFromLegacyStorage = false;

    public static RipperdocConfig loadOrMigrate(MinecraftServer server) {
        RipperdocConfig config = null;
        if (Files.isRegularFile(PATH)) {
            try {
                config = GSON.fromJson(Files.readString(PATH, StandardCharsets.UTF_8), RipperdocConfig.class);
            } catch (Exception e) {
                RipperdocMod.LOGGER.error("Could not read {}; defaults will be used", PATH, e);
            }
        }
        if (config == null) {
            config = new RipperdocConfig();
            config.importLegacyStorage(server);
        }
        config.validate();
        config.save();
        return config;
    }

    private void importLegacyStorage(MinecraftServer server) {
        try {
            CompoundTag root = server.getCommandStorage().get(Identifier.parse("ripperdoc:config"));
            if (root == null || root.isEmpty()) return;
            CompoundTag zande = root.getCompoundOrEmpty("zande");
            CompoundTag berserk = root.getCompoundOrEmpty("berserk");
            if (zande.contains("speed_percent")) {
                zandeSpeedPercent = zande.getIntOr("speed_percent", 50);
            } else if (zande.contains("speed")) {
                zandeSpeedPercent = (int)Math.round(zande.getDoubleOr("speed", 0.5) * 100.0);
            }
            if (berserk.contains("attack")) berserkAttack = berserk.getDoubleOr("attack", 6.0);
            if (berserk.contains("mining_percent")) {
                berserkMiningPercent = berserk.getIntOr("mining_percent", 60);
            } else if (berserk.contains("mining")) {
                berserkMiningPercent = (int)Math.round(berserk.getDoubleOr("mining", 0.6) * 100.0);
            }
            migratedFromLegacyStorage = true;
            RipperdocMod.LOGGER.info("Imported legacy Ripperdoc config: speed={}%, attack={}, mining={}%",
                    zandeSpeedPercent, berserkAttack, berserkMiningPercent);
        } catch (Exception e) {
            RipperdocMod.LOGGER.warn("Legacy command-storage config could not be imported; defaults will be used", e);
        }
    }

    public void validate() {
        zandeSpeedPercent = Math.max(0, Math.min(300, zandeSpeedPercent));
        berserkAttack = Math.max(0.0, Math.min(100.0, berserkAttack));
        berserkMiningPercent = Math.max(0, Math.min(500, berserkMiningPercent));
    }

    public void reset() {
        zandeSpeedPercent = 50;
        berserkAttack = 6.0;
        berserkMiningPercent = 60;
        save();
    }

    public double zandeMultiplier() { return zandeSpeedPercent / 100.0; }
    public double berserkMiningMultiplier() { return berserkMiningPercent / 100.0; }

    public void save() {
        validate();
        try {
            Files.createDirectories(PATH.getParent());
            Files.writeString(PATH, GSON.toJson(this) + "\n", StandardCharsets.UTF_8);
        } catch (IOException e) {
            RipperdocMod.LOGGER.error("Could not save {}", PATH, e);
        }
    }
}
