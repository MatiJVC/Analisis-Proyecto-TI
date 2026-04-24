export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-20">
        <div className="text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            Bienvenido al Proyecto TI
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Frontend con Next.js + Tailwind CSS
          </p>
          
          <div className="grid md:grid-cols-3 gap-6 mt-12">
            <div className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow">
              <h2 className="text-2xl font-bold text-indigo-600 mb-2">Next.js</h2>
              <p className="text-gray-600">Framework moderno para React</p>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow">
              <h2 className="text-2xl font-bold text-indigo-600 mb-2">Tailwind</h2>
              <p className="text-gray-600">Estilos CSS modernos y utilitarios</p>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow">
              <h2 className="text-2xl font-bold text-indigo-600 mb-2">Power BI</h2>
              <p className="text-gray-600">Reportes y dashboards integrados</p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
