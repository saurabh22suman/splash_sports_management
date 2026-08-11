import { TrendingUp, Users, ArrowUpRight } from 'lucide-react';

export default function MembershipsAndDashboard() {
  return (
    <div className="bg-charcoal-900">
      
      {/* Membership Section */}
      <section className="py-24 lg:py-32 border-t border-charcoal-800">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <h2 className="text-5xl md:text-6xl font-display font-bold leading-[0.9] mb-6">
              MEMBERSHIPS THAT<br />
              <span className="text-volt">RUN THEMSELVES.</span>
            </h2>
            <p className="text-gray-400 font-medium max-w-md mb-8">
              Automate renewals, track attendance patterns, and predict churn before it happens. Keep your focus on the club, not the paperwork.
            </p>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-charcoal-800 border border-charcoal-700 p-6 flex flex-col justify-between h-48 hover:border-charcoal-600 transition-colors">
              <div className="flex justify-between items-start">
                <Users className="text-gray-400" />
                <span className="text-xs font-mono text-green-400 flex items-center gap-1">
                  <ArrowUpRight size={14} /> 12.4%
                </span>
              </div>
              <div>
                <div className="font-display text-5xl text-white mb-1">2,481</div>
                <div className="text-xs font-bold tracking-widest text-gray-500 uppercase">Active Members</div>
              </div>
            </div>
            
            <div className="bg-volt text-black p-6 flex flex-col justify-between h-48">
              <div className="flex justify-between items-start">
                <TrendingUp />
              </div>
              <div>
                <div className="font-display text-5xl mb-1">86%</div>
                <div className="text-xs font-bold tracking-widest uppercase opacity-80">Renewal Rate</div>
              </div>
            </div>
            
            <div className="col-span-2 bg-charcoal-950 border border-charcoal-800 p-6 flex items-center justify-between">
              <div>
                <div className="font-display text-2xl text-white">42 Expiring Soon</div>
                <div className="text-xs font-mono text-gray-500 mt-1">Automated WhatsApp Reminders Active</div>
              </div>
              <div className="w-12 h-6 rounded-full bg-volt/20 flex items-center p-1 cursor-pointer">
                <div className="w-4 h-4 rounded-full bg-volt translate-x-6 shadow-md"></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Owner Dashboard Showcase */}
      <section className="py-24 bg-charcoal-950 border-t border-charcoal-800 overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-xs font-bold tracking-widest text-gray-500 uppercase mb-4">Command Center</h2>
            <h3 className="text-4xl md:text-5xl font-display font-bold text-white">
              YOUR ENTIRE BUSINESS.<br />AT A GLANCE.
            </h3>
          </div>
          
          {/* Dashboard UI Mockup */}
          <div className="w-full max-w-5xl mx-auto bg-charcoal-900 rounded-t-xl border border-charcoal-700 border-b-0 shadow-2xl overflow-hidden relative">
            <div className="h-12 bg-charcoal-950 border-b border-charcoal-800 flex items-center px-4 gap-2">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
              </div>
              <div className="mx-auto text-xs font-mono text-gray-500">splashh.app/dashboard</div>
            </div>
            
            <div className="p-6 md:p-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { label: "TODAY'S REVENUE", value: "₹48,250", trend: "↑ 14.2%", positive: true },
                { label: "OCCUPANCY", value: "82%", trend: "Peak hours", positive: true },
                { label: "RENEWALS", value: "24", trend: "This Week", positive: true },
                { label: "ACTIVE MEMBERS", value: "1,284", trend: "+12 New", positive: true }
              ].map((stat, i) => (
                <div key={i} className="bg-charcoal-800 border border-charcoal-700 p-5 rounded-lg">
                  <div className="text-[10px] font-bold tracking-widest text-gray-400 uppercase mb-2">{stat.label}</div>
                  <div className="font-display text-3xl text-white mb-2">{stat.value}</div>
                  <div className={`text-xs font-mono ${stat.positive ? 'text-green-400' : 'text-red-400'}`}>{stat.trend}</div>
                </div>
              ))}
              
              <div className="col-span-1 md:col-span-2 lg:col-span-3 h-64 bg-charcoal-800 border border-charcoal-700 rounded-lg p-5 relative overflow-hidden">
                <div className="text-[10px] font-bold tracking-widest text-gray-400 uppercase mb-4">Revenue Trend</div>
                {/* Abstract Chart */}
                <div className="absolute bottom-0 left-0 right-0 h-3/4 flex items-end justify-between px-5 pb-5 gap-2">
                  {[40, 60, 45, 80, 50, 90, 75, 100, 85, 95].map((h, i) => (
                    <div key={i} className="w-full bg-volt/20 hover:bg-volt transition-colors rounded-t-sm" style={{ height: `${h}%` }}></div>
                  ))}
                </div>
              </div>
              
              <div className="col-span-1 h-64 bg-charcoal-800 border border-charcoal-700 rounded-lg p-5 flex flex-col">
                <div className="text-[10px] font-bold tracking-widest text-gray-400 uppercase mb-4">Upcoming</div>
                <div className="space-y-3 flex-1 overflow-hidden">
                  <div className="flex justify-between items-center text-sm border-b border-charcoal-700 pb-2">
                    <span className="text-gray-300">Court 1</span>
                    <span className="text-volt font-mono">18:00</span>
                  </div>
                  <div className="flex justify-between items-center text-sm border-b border-charcoal-700 pb-2">
                    <span className="text-gray-300">Pool Batch A</span>
                    <span className="text-volt font-mono">18:30</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-300">Court 3</span>
                    <span className="text-volt font-mono">19:00</span>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Gradient fade at bottom to hide the cutoff */}
            <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-charcoal-950 to-transparent"></div>
          </div>
        </div>
      </section>
      
    </div>
  );
}
