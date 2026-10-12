using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using LevelUp.NavTableUpdater.Core.Aircraft;
using LevelUp.NavTableUpdater.Core.Content;
using LevelUp.NavTableUpdater.Core.Manifest;
using LevelUp.NavTableUpdater.Core.State;
string Config(string name)=>Environment.GetEnvironmentVariable(name) is { Length: > 0 } value?Path.GetFullPath(value):throw new InvalidOperationException("Set "+name+"; see tests/README.md");
var project=Config("TIMER_PROJECT_ROOT");
var ziboBaseline=Config("TIMER_ZIBO_AIRCRAFT");
var levelupBaseline=Config("TIMER_LEVELUP_AIRCRAFT");
var luScripts=Config("TIMER_LEVELUP_SCRIPTS");
var root=Path.Combine(project,"artifacts","mtk-run-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(Path.Combine(root,"logs"));File.WriteAllText(Path.Combine(project,"artifacts/mtk-latest.txt"),root);
var catalog=ContentPackageCatalog.Parse(File.ReadAllText(Path.Combine(project,"artifacts/dev-catalog.json")),new Version(0,28,2));
var results=new List<object>();int failures=0;
string Hash(byte[] b)=>Convert.ToHexStringLower(SHA256.HashData(b));
void Require(bool condition,string error){if(!condition)throw new Exception(error);}
Dictionary<string,string> Snapshot(string dir,bool active=false)=>Directory.Exists(dir)?Directory.GetFiles(dir,"*",SearchOption.AllDirectories).Where(p=>!active||(!p.EndsWith(".bak")&&!p.EndsWith(".py"))).ToDictionary(p=>Path.GetRelativePath(dir,p),p=>Hash(File.ReadAllBytes(p))):[];
void Same(Dictionary<string,string> expected,string dir,string label,bool active=false){var now=Snapshot(dir,active);var diff=expected.Keys.Concat(now.Keys).Distinct().Where(p=>expected.GetValueOrDefault(p)!=now.GetValueOrDefault(p)).ToArray();Require(diff.Length==0,"Snapshot changed: "+label+": "+string.Join(",",diff.Take(10)));}
async Task Check(string name,Func<Task> task){if(args.Length>0&&!args.Any(filter=>name.Contains(filter)))return;try{await task();results.Add(new{name,status="PASS"});Console.WriteLine("PASS "+name);}catch(Exception ex){failures++;results.Add(new{name,status="FAIL",error=ex.ToString()});Console.WriteLine("FAIL "+name+": "+ex.Message);}}
var groups=new[]{"zibo-737ng","levelup-737ng"}.ToDictionary(p=>p,p=>Path.Combine(project,"artifacts",p+"-v1"));
const string Fms="plugins/xlua/scripts/B738.a_fms/B738.a_fms.lua";
(string Case,string Aircraft,AircraftVariantViewAnalysis Variant,ToolStateStore Store,CompatibilityPackageOperation Operation) Setup(string name,string product){
 var path=Path.Combine(root,"cases",name);Require(!Directory.Exists(path),"Output already exists: "+path);var aircraft=Path.Combine(path,"aircraft");Directory.CreateDirectory(aircraft);
 var manifest=CompatibilityPackageLoader.LoadDirectory(groups[product]).Manifest;
 var baseline=product=="zibo-737ng"?ziboBaseline:levelupBaseline;
 var timerFiles=new[]{"B738.a_AXP_4_FMOD_logic","B738.a_fms","B738.anav","B738.calc","B738.glaresheild","B738.LATLON","B738.tablet","B738.zz.sim_cockpit","B738.ZZZ_AXP_5_added_logic_ULTIMATE"}.Select(m=>$"plugins/xlua/scripts/{m}/{m}.lua");
 var paths=manifest.Modules.SelectMany(m=>m.Targets.Select(t=>t.RelativePath).Concat(m.RetiredFiles.Select(f=>f.RelativePath))).Concat(timerFiles).Concat(Directory.GetFiles(baseline,"*.acf").Select(Path.GetFileName)!).Distinct();
 var inputs=new List<object>();foreach(var relative in paths){if(relative is null)continue;var from=Path.Combine(baseline,relative);if(product=="levelup-737ng"&&File.Exists(Path.Combine(luScripts,relative)))from=Path.Combine(luScripts,relative);if(!File.Exists(from))continue;var to=Path.Combine(aircraft,relative);Directory.CreateDirectory(Path.GetDirectoryName(to)!);File.Copy(from,to);inputs.Add(new{relative,source=from,sha256=Hash(File.ReadAllBytes(from))});}

 File.WriteAllText(Path.Combine(aircraft,"unrelated-sentinel.txt"),"unrelated data must survive\n");
 var acf=Path.Combine(aircraft,product=="zibo-737ng"?"b738.acf":"737_80NG.acf");
 var v=new AircraftVariantViewAnalysis(product=="zibo-737ng"?"zibo-737-800":"levelup-737-800",product,product,acf,Path.ChangeExtension(acf,null)+"_prefs.txt","fixture","fixture",product=="zibo-737ng"?"4.05.35":"V2.S1.51C",null,null,null,null,null,0,0,null,null,null,null,"fixture","fixture","fixture","fixture");
 var store=new ToolStateStore(Path.Combine(path,"state"),Path.Combine(path,"backups"));var op=new CompatibilityPackageOperation(store,()=>false,()=>catalog);
 File.WriteAllText(Path.Combine(path,"original-inputs.json"),JsonSerializer.Serialize(inputs,new JsonSerializerOptions{WriteIndented=true}));return(path,aircraft,v,store,op);
}
const string Helper="plugins/xlua/scripts/B738.a_fms/B738.wahltho_timer.lua";
var package1=Path.Combine(project,"artifacts/package-v1");
void Python(string aircraft, string? state=null, bool uninstall=false, bool blocked=false) {
 var psi=new ProcessStartInfo("python3"){RedirectStandardOutput=true,RedirectStandardError=true};
 // Process detection is a boundary stub for disposable fixtures only.
 psi.ArgumentList.Add("-c");psi.ArgumentList.Add("import sys; from unittest.mock import patch,Mock; sys.path.insert(0,sys.argv[1]); import z_Install,standalone_guard;\nwith patch.object(standalone_guard.subprocess,'run',return_value=Mock(stdout='')): z_Install.run(sys.argv[2],sys.argv[3]=='uninstall')");
 psi.ArgumentList.Add(project);psi.ArgumentList.Add(aircraft);psi.ArgumentList.Add(uninstall?"uninstall":"install");
 if(state is not null)psi.Environment["MTK_STATE_PATH"]=state;
 using var process=Process.Start(psi)!;var output=process.StandardOutput.ReadToEnd()+process.StandardError.ReadToEnd();process.WaitForExit();
 File.AppendAllText(Path.Combine(root,"logs/standalone.txt"),aircraft+"\n"+output+"\n");Require(blocked?process.ExitCode!=0:process.ExitCode==0,"Standalone boundary: "+output);
}
void Syntax(string aircraft){
 var psi=new ProcessStartInfo(Path.Combine(project,"artifacts/runtime_probe")){RedirectStandardOutput=true,RedirectStandardError=true};
 foreach(var file in new[]{Fms,Helper,"plugins/xlua/scripts/B738.tablet/B738.tablet.lua","plugins/xlua/scripts/B738.calc/B738.calc.lua"})psi.ArgumentList.Add(Path.Combine(aircraft,file));
 using var process=Process.Start(psi)!;var output=process.StandardOutput.ReadToEnd()+process.StandardError.ReadToEnd();process.WaitForExit();File.AppendAllText(Path.Combine(root,"logs/syntax.txt"),output);Require(process.ExitCode==0,"Patched Lua syntax: "+output);
}
void SameCallbacks(string before,string after){
 foreach(var callback in new[]{"before_physics","after_physics"}){
  var needle="function "+callback+"()";var at=before.IndexOf(needle,StringComparison.Ordinal);if(at<0)continue;
  Require(after[after.IndexOf(needle,StringComparison.Ordinal)..]==before[at..],"Changed original callback tail: "+callback);
 }
 Require(after.Split("SIM_PERIOD").Length==before.Split("SIM_PERIOD").Length,"Changed SIM_PERIOD references");
 Require(!after.Contains("function timed_after_physics("),"Legacy timer callback present");
}
await Check("archive-adapter-schema3-and-unselected-module",async()=>{
 using var bytes=new MemoryStream();
 using(var archive=new System.IO.Compression.ZipArchive(bytes,System.IO.Compression.ZipArchiveMode.Create,true)){
  foreach(var file in Directory.GetFiles(package1,"*",SearchOption.AllDirectories).Where(f=>f.EndsWith("package-manifest.json")||f.Contains(Path.DirectorySeparatorChar+"modules"+Path.DirectorySeparatorChar))){
   var entry=archive.CreateEntry(Path.GetRelativePath(package1,file).Replace('\\','/'));using var stream=entry.Open();stream.Write(File.ReadAllBytes(file));
  }
 }
 var archiveBytes=bytes.ToArray();var source=catalog.Packages.Single(p=>p.PackageId=="wahltho.zibo-levelup-737ng.lua-timer");var group=catalog.Packages.Single(p=>p.PackageId=="wahltho.zibo-40535.maintenance");var member=group.Members.Single(m=>m.ModuleId=="lua-timer");
 var version=CompatibilityPackageLoader.LoadDirectory(package1).Manifest.PackageVersion;var tag="v"+version;var asset="X-Plane-Zibo-LevelUp-Lua-Timer-Mod-"+tag+".zip";
 var release=new ContentPatchRelease(tag,source.RepositoryUrl+"/releases/tag/"+tag,asset,source.RepositoryUrl+"/releases/download/"+tag+"/"+asset,archiveBytes.Length,Hash(archiveBytes));
 using var client=new HttpClient(new ArchiveHandler(archiveBytes));var adapter=new GitHubContentPatchReleaseSource(client,Path.Combine(root,"adapter-cache"));
 var result=await adapter.ProvisionGroupAsync(new(group,[(member,source,release)],"catalog-timer-test"));
 var reloaded=CompatibilityPackageLoader.LoadDirectory(result.PackageDirectory);
 Require(reloaded.Manifest.SchemaVersion==3,"Schema lost during source conversion");Require(reloaded.Manifest.Sources.Single().PackageId==source.PackageId,"Source owner lost");
 Require(!CompatibilityPackagePlanBuilder.DefaultSelection(reloaded.Manifest).Contains("lua-timer"),"Adapter enabled optional module");
 var expected=CompatibilityPackageLoader.LoadDirectory(package1).Manifest.Modules.Single();var actual=reloaded.Manifest.Modules.Single();
 Require(actual.InstallationOrder==90&&actual.Policy==CompatibilityModulePolicy.Optional,"Optional policy/order lost");
 Require(actual.Payloads.All(p=>expected.Payloads.Any(e=>e.Path==p.Path&&e.Size==p.Size&&e.Sha256==p.Sha256)),"Payload inventory changed");Require(actual.Targets.Count==expected.Targets.Count,"Targets lost");
});
foreach(var product in groups.Keys){
 var dir=groups[product];var dir2=Path.Combine(project,"artifacts",product+"-v2");
 var manifest=CompatibilityPackageLoader.LoadDirectory(dir).Manifest;var all=manifest.Modules.Select(m=>m.ModuleId).ToArray();var old=all.Where(m=>m!="lua-timer").ToArray();
 Require(!CompatibilityPackagePlanBuilder.DefaultSelection(manifest).Contains("lua-timer"),"Timer selected by default");
 await Check(product+"-existing-all-patches-add-timer-deselect-readd-restore",async()=>{
  var x=Setup(product+"-existing",product);var original=Snapshot(x.Aircraft,true);
  var r=await x.Operation.RunAsync(ContentPatchAction.Install,x.Variant,dir,old);Require(r.Succeeded,r.Message);var existing=Snapshot(x.Aircraft,true);var before=File.ReadAllText(Path.Combine(x.Aircraft,Fms));
  r=await x.Operation.RunAsync(ContentPatchAction.Update,x.Variant,dir,all);Require(r.Succeeded,r.Message);var installed=Snapshot(x.Aircraft,true);
  SameCallbacks(before,File.ReadAllText(Path.Combine(x.Aircraft,Fms)));foreach(var f in existing.Keys.Where(f=>f!=Fms))Require(installed[f]==existing[f],"Changed unrelated patch file "+f);
  foreach(var action in new[]{ContentPatchAction.Install,ContentPatchAction.Update,ContentPatchAction.Repair}){r=await x.Operation.RunAsync(action,x.Variant,dir,all);Require(r.Succeeded,r.Message);Same(installed,x.Aircraft,"repeat "+action,true);}
  r=await x.Operation.RunAsync(ContentPatchAction.Update,x.Variant,dir,old);Require(r.Succeeded,r.Message);Same(existing,x.Aircraft,"Timer deselection retains every existing patch",true);
  r=await x.Operation.RunAsync(ContentPatchAction.Update,x.Variant,dir,all);Require(r.Succeeded,r.Message);Same(installed,x.Aircraft,"Timer readdition",true);
  // Check every other optional module with Timer kept selected.
  foreach(var module in manifest.Modules.Where(m=>m.Policy!=CompatibilityModulePolicy.Required&&m.ModuleId!="lua-timer")){
   var selection=all.Where(m=>m!=module.ModuleId).ToArray();r=await x.Operation.RunAsync(ContentPatchAction.Update,x.Variant,dir,selection);Require(r.Succeeded,"Deselect "+module.ModuleId+": "+r.Message);
   r=await x.Operation.RunAsync(ContentPatchAction.Update,x.Variant,dir,all);Require(r.Succeeded,"Re-add "+module.ModuleId+": "+r.Message);Same(installed,x.Aircraft,"other module readdition",true);
  }
  r=x.Operation.Restore(x.Variant,dir);Require(r.Succeeded,r.Message);Same(original,x.Aircraft,"complete group Restore",true);
 });
 await Check(product+"-timer-first-managed-adoption-by-group",async()=>{
  var x=Setup(product+"-timer-first",product);var original=Snapshot(x.Aircraft,true);var before=File.ReadAllText(Path.Combine(x.Aircraft,Fms));
  var r=await x.Operation.RunAsync(ContentPatchAction.Install,x.Variant,package1,["lua-timer"]);Require(r.Succeeded,r.Message);SameCallbacks(before,File.ReadAllText(Path.Combine(x.Aircraft,Fms)));
  r=await x.Operation.RunAsync(ContentPatchAction.Update,x.Variant,dir,all);Require(r.Succeeded,r.Message);
  r=x.Operation.Restore(x.Variant,dir);Require(r.Succeeded,r.Message);Same(original,x.Aircraft,"single owner to group restore",true);
 });
 await Check(product+"-actual-new-helper-version-update-and-original-restore",async()=>{
  var x=Setup(product+"-version",product);var original=Snapshot(x.Aircraft,true);
  var r=await x.Operation.RunAsync(ContentPatchAction.Install,x.Variant,dir,all);Require(r.Succeeded,r.Message);var first=Hash(File.ReadAllBytes(Path.Combine(x.Aircraft,Helper)));
  r=await x.Operation.RunAsync(ContentPatchAction.Update,x.Variant,dir2,all);Require(r.Succeeded,r.Message);
  Require(Hash(File.ReadAllBytes(Path.Combine(x.Aircraft,Helper)))!=first,"Version update made no helper change");Require(File.ReadAllText(Path.Combine(x.Aircraft,Helper)).Contains("local age = 0.04"),"Wrong updated helper");
  var updated=Snapshot(x.Aircraft,true);r=await x.Operation.RunAsync(ContentPatchAction.Repair,x.Variant,dir2,all);Require(r.Succeeded,r.Message);Same(updated,x.Aircraft,"Repair after version change",true);
  r=x.Operation.Restore(x.Variant,dir2);Require(r.Succeeded,r.Message);Same(original,x.Aircraft,"original generation after real update",true);
 });
 await Check(product+"-uninstall-retains-prior-patches",async()=>{
  var x=Setup(product+"-uninstall",product);var original=Snapshot(x.Aircraft,true);
  var r=await x.Operation.RunAsync(ContentPatchAction.Install,x.Variant,dir,all);Require(r.Succeeded,r.Message);
  r=await x.Operation.RunAsync(ContentPatchAction.Uninstall,x.Variant,dir,all);Require(r.Succeeded,r.Message);Same(original,x.Aircraft,"Uninstall originals",true);
 });
 await Check(product+"-standalone-and-MTK-owner-boundaries",async()=>{
  var x=Setup(product+"-standalone",product);var original=Snapshot(x.Aircraft,true);Python(x.Aircraft);var standalone=Snapshot(x.Case);
  var r=await x.Operation.RunAsync(ContentPatchAction.Install,x.Variant,dir,all);Require(!r.Succeeded,"Adopted standalone owner");Same(standalone,x.Case,"Standalone blocks MTK");
  Python(x.Aircraft,uninstall:true);var clean=Snapshot(x.Aircraft,true);Require(original.All(pair=>clean.GetValueOrDefault(pair.Key)==pair.Value),"Standalone did not restore original aircraft files");Require(clean.Keys.Except(original.Keys).All(path=>path.StartsWith(".patch-ownership/",StringComparison.Ordinal)),"Standalone left active payload files");
  r=await x.Operation.RunAsync(ContentPatchAction.Install,x.Variant,dir,all);Require(r.Succeeded,r.Message);Syntax(x.Aircraft);var managed=Snapshot(x.Case);
  Python(x.Aircraft,x.Store.StatePath,blocked:true);Same(managed,x.Case,"MTK blocks standalone");
 });
 await Check(product+"-unknown-and-identical-unowned-files-block",async()=>{
  var x=Setup(product+"-unknown",product);File.Copy(Path.Combine(project,"modules/lua-timer/payload/B738.wahltho_timer.lua"),Path.Combine(x.Aircraft,Helper));var snapshot=Snapshot(x.Case);
  var r=await x.Operation.RunAsync(ContentPatchAction.Install,x.Variant,dir,all);Require(!r.Succeeded,"Adopted identical unowned helper");Same(snapshot,x.Case,"Unowned helper block");
  File.Delete(Path.Combine(x.Aircraft,Helper));File.AppendAllText(Path.Combine(x.Aircraft,Fms),"\n-- BEGIN WAHLTHO_LUA_TIMER UNKNOWN\n-- END WAHLTHO_LUA_TIMER UNKNOWN\n");snapshot=Snapshot(x.Case);
  r=await x.Operation.RunAsync(ContentPatchAction.Install,x.Variant,dir,all);Require(!r.Succeeded,"Unknown namespace accepted");Same(snapshot,x.Case,"Unknown namespace block");
 });
 await Check(product+"-pre-execute-source-change-blocks",async()=>{
  var x=Setup(product+"-race",product);var plan=await x.Operation.PlanAsync(ContentPatchAction.Install,x.Variant,dir,all);Require(plan.IsSafe,plan.StatusMessage);
  File.AppendAllText(Path.Combine(x.Aircraft,Fms),"\n-- change after plan\n");var snapshot=Snapshot(x.Case);
  var r=new ContentPatchEngine(x.Store,()=>false,()=>catalog).Execute(plan,x.Variant);Require(!r.Succeeded,"Race allowed");Same(snapshot,x.Case,"Pre-execute change block");
 });
 await Check(product+"-modified-managed-files-block-all-operations",async()=>{
  var x=Setup(product+"-changed",product);var r=await x.Operation.RunAsync(ContentPatchAction.Install,x.Variant,dir,all);Require(r.Succeeded,r.Message);
  File.AppendAllText(Path.Combine(x.Aircraft,Helper),"\n-- user change\n");var snapshot=Snapshot(x.Case);
  foreach(var action in new[]{ContentPatchAction.Install,ContentPatchAction.Update,ContentPatchAction.Repair,ContentPatchAction.Uninstall}){r=await x.Operation.RunAsync(action,x.Variant,dir,all);Require(!r.Succeeded,"Changed file accepted "+action);Same(snapshot,x.Case,"Block "+action);}
  r=x.Operation.Restore(x.Variant,dir);Require(!r.Succeeded,"Restore overwrote modified helper");Same(snapshot,x.Case,"Restore block");
 });
 await Check(product+"-injected-final-scope-failure-rolls-back-written-files",async()=>{
  var x=Setup(product+"-rollback",product);var original=Snapshot(x.Aircraft,true);
  var plan=await x.Operation.PlanAsync(ContentPatchAction.Install,x.Variant,dir,all);Require(plan.IsSafe,plan.StatusMessage);
  var folder=Path.Combine(x.Aircraft,"plugins/xlua/scripts/B738.a_fms");
  var scope=new ContentPatchScopeSnapshot("plugins/xlua/scripts/B738.a_fms",true,Directory.GetFiles(folder).ToDictionary(f=>Path.GetFileName(f),f=>Hash(File.ReadAllBytes(f))));
  // Inject a stale final allowlist after planning. It must fail only after
  // writes, at final scope verification, and roll back the whole transaction.
  var fault=plan with {ExpectedScopes=[scope],FinalScopes=[scope]};bool failed=false;
  try {new ContentPatchEngine(x.Store,()=>false,()=>catalog).Execute(fault,x.Variant);}
  catch(InvalidOperationException ex){failed=true;Require(ex.Message.Contains("scope",StringComparison.OrdinalIgnoreCase),"Wrong injected failure: "+ex.Message);}
  Require(failed,"Injected final verification did not fail");Same(original,x.Aircraft,"Rollback after writes",true);Require(!File.Exists(x.Store.StatePath),"Unexpected state commit");
 });
}
File.WriteAllText(Path.Combine(root,"logs/results.json"),JsonSerializer.Serialize(new{coreVersion=typeof(ContentPackageCatalog).Assembly.GetName().Version!.ToString(),catalog.CatalogVersion,failures,results},new JsonSerializerOptions{WriteIndented=true}));
Console.WriteLine("RESULT failures="+failures+" cases="+results.Count+" path="+root);if(failures>0)Environment.Exit(1);

sealed class ArchiveHandler(byte[] bytes):HttpMessageHandler {
 protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken token)=>Task.FromResult(new HttpResponseMessage(System.Net.HttpStatusCode.OK){Content=new ByteArrayContent(bytes)});
}
