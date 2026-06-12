export default function Dashboard() {
  return (
    <main className="min-h-screen p-10 max-w-6xl mx-auto">
      <header className="mb-12 border-b border-neutral-800 pb-6 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-white mb-2">Content OS</h1>
          <p className="text-neutral-500">Autonomous Video Pipeline</p>
        </div>
        <div className="px-3 py-1 bg-green-500/10 text-green-400 text-xs rounded-full border border-green-500/20">
          System Online
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-[#171717] border border-neutral-800 rounded-lg p-5 hover:border-neutral-700 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <h2 className="project-name">The Rome Empire</h2>
            <span className="text-[10px] uppercase font-bold text-yellow-500 bg-yellow-500/10 px-2 py-1 rounded">Rendering</span>
          </div>
          <p className="text-sm text-neutral-400 mb-4 line-clamp-2">
            Educational short explaining the engineering marvels of the Roman aqueducts.
          </p>
          <div className="w-full bg-neutral-800 rounded-full h-1.5 mb-4 overflow-hidden">
            <div className="bg-white h-1.5 rounded-full w-2/3"></div>
          </div>
        </div>

        <div className="bg-transparent border border-dashed border-neutral-700 rounded-lg p-5 flex flex-col items-center justify-center text-neutral-500 hover:text-white hover:border-neutral-500 transition-all cursor-pointer">
          <span className="text-2xl mb-2">+</span>
          <span className="text-sm">Manual Trigger</span>
        </div>
      </div>
    </main>
  );
}
