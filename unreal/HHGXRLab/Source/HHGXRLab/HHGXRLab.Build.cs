using UnrealBuildTool;

public class HHGXRLab : ModuleRules
{
    public HHGXRLab(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[]
        {
            "Core",
            "CoreUObject",
            "Engine",
            "Json",
            "JsonUtilities",
            "ProceduralMeshComponent",
        });

        PrivateDependencyModuleNames.AddRange(new string[] { });
    }
}
