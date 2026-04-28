export type Language = "en" | "es";

export const translations = {
  en: {
    // Sidebar
    hospitalityAi: "Hospitality AI",
    aiAssistantActive: "AI Assistant Active",
    newChat: "New Chat",
    chatHistory: "Chat History",
    seeAllHistory: "See all history",
    features: "Features",
    kpiAnalysis: "KPI Analysis",
    hrOptimization: "HR Optimization",
    beverageInsights: "Beverage Insights",
    menuEngineering: "Menu Engineering",
    recipeIntelligence: "Recipe Intelligence",
    strategicPlanning: "Strategic Planning",
    csvKpiDashboard: "CSV KPI Dashboard",
    userProfile: "User Profile",
    selectLanguage: "Select language",
    
    // Chat History
    chatHistoryTitle: "Your Hospitality AI Assistant",
    chatHistorySubtitle: "Find Your All Chat history here",
    allTypes: "All types",
    titleAndDescription: "Title & Description",
    date: "Date",
    noChatHistory: "No chat history found",

    // Mobile Header
    dashboard: "Dashboard",

    // KPI Analysis Page
    kpiAnalysisTitle: "KPI Analysis",
    kpiAnalysisSubtitle:
      "Analyze labor cost, prime cost, and sales performance with\nAI-powered benchmarking and recommendations.",
    laborCostAnalysis: "Labor Cost Analysis",
    laborCostPercentage: "Labor cost percentage",
    overtimeTracking: "Overtime tracking",
    productivityMetrics: "Productivity metrics",
    primeCostAnalysis: "Prime Cost Analysis",
    primeCostPercentage: "Prime cost percentage",
    targetBenchmarking: "Target benchmarking",
    trendAnalysis: "Trend analysis",
    salesPerformance: "Sales Performance",
    salesPerLaborHour: "Sales per labor hour",
    revenueTrends: "Revenue trends",
    growthAnalysis: "Growth analysis",
    kpiInputPlaceholder:
      "Enter: Total Sale, Labor Cost, Hours Worked (e.g., 10000, 3000, 120)",
    pressEnterToSend: "Press Enter to send, Shift + Enter for new line",
    error: "Error",
    kpiLaborSample: "Analyze my labor cost. Total sales: $50,000. Labor cost: $15,000. Hours worked: 800. Overtime hours: 40. Covers served: 2,000.",
    kpiPrimeSample: "Analyze my prime cost. Total sales: $50,000. Labor cost: $15,000. Food cost: $14,000. Covers served: 2,000.",
    kpiSalesSample: "Analyze my sales performance. Total sales: $50,000. Labor cost: $15,000. Food cost: $14,000. Hours worked: 800. Previous sales: $48,000. Covers served: 2,000. Average check: $25.",

    // HR Optimization Page
    hrOptimizationTitle: "HR Optimization",
    hrOptimizationSubtitle:
      "Optimize your workforce management with AI-driven insights\nfor retention, scheduling, and performance tracking.",
    staffRetention: "Staff Retention",
    turnoverAnalysis: "Turnover analysis",
    retentionStrategies: "Retention strategies",
    costImpactAssessment: "Cost impact assessment",
    laborScheduling: "Labor Scheduling",
    shiftOptimization: "Shift optimization",
    peakHourCoverage: "Peak hour coverage",
    overtimeManagement: "Overtime management",
    trainingPrograms: "Training Programs",
    onboardingOptimization: "Onboarding optimization",
    skillDevelopment: "Skill development",
    performanceTracking: "Performance tracking",
    hrInputPlaceholder:
      "Enter HR inputs as key:value pairs (e.g., turnover_rate: 45, industry_average: 70)",
    hrRetentionSample: "Staff retention sample: turnover_rate: 0.45, industry_average: 0.70, department: Front of House, employee_count: 25",
    hrSchedulingSample: "Labor scheduling sample: total_sales: 50000, labor_hours: 800, hourly_rate: 15, peak_hours: 200, date: 2026-02-01, department: Kitchen.",
    hrPerformanceSample: "Training programs sample: customer_satisfaction: 0.85, sales_performance: 0.95, efficiency_score: 0.80, attendance_rate: 0.92, employee name: Alex Rivera, department: Service",

    // Beverage Insights Page
    beverageInsightsTitle: "Beverage Insights",
    beverageInsightsSubtitle:
      "Optimize your bar operations with comprehensive analytics\nfor liquor costs, inventory management, and pricing strategies.",
    liquorCostAnalysis: "Liquor Cost Analysis",
    varianceAnalysis: "Variance analysis",
    costPerOunceTracking: "Cost per ounce tracking",
    wasteIdentification: "Waste identification",
    barInventoryManagement: "Bar Inventory Management",
    stockLevelTracking: "Stock level tracking",
    reorderOptimization: "Reorder optimization",
    inventoryValuation: "Inventory valuation",
    beveragePricing: "Beverage Pricing",
    marginAnalysis: "Margin analysis",
    competitivePricing: "Competitive pricing",
    profitOptimization: "Profit optimization",
    beverageInputPlaceholder:
      "Enter: Total Beverage Sales, Beverage Cost, Pour Cost % (e.g., $50000, $12000, 24%)",
    bevLiquorSample: "Liquor Cost Analysis:\nExpected oz: 1500, Actual oz: 1650, Liquor cost: $3500, Total sales: $15000, Bottle cost: $25, Bottle size oz: 25, Target cost percentage: 20%",
    bevBarSample: "Bar Inventory Analysis:\nCurrent stock: 800, Reorder point: 250, Monthly usage: 600, Inventory value: $12500, Lead time days: 7, Safety stock: 100, Item cost: $12.5, Target turnover: 12",
    bevPricingSample: "Beverage Pricing Analysis:\nDrink price: $12, Cost per drink: $3, Sales volume: 1800, Competitor price: $11, Target margin: 75%, Market position: premium, Elasticity factor: 1.5",

    // Menu Engineering Page
    menuAnalysisTitle: "Menu Analysis",
    salesMixAnalysis: "Sales mix analysis",
    contributionMargins: "Contribution margins",
    menuMatrixMapping: "Menu matrix mapping",
    pricingStrategyTitle: "Pricing Strategy",
    priceElasticity: "Price elasticity",
    competitiveAnalysis: "Competitive analysis",
    profitMaximization: "Profit maximization",
    itemOptimizationTitle: "Item Optimization",
    recipeCosting: "Recipe costing",
    portionControl: "Portion control",
    descriptionOptimization: "Description optimization",
    menuEngineeringSubtitle: "Transform your menu into a profit driver with data-driven insights\non product mix, pricing strategies, and design optimization.",
    menuInputPlaceholder: "Select a card to load a sample prompt, or type menu item details...",
    menuFooterHint: "Press Enter to send  Shift + Enter for new line   to upload CSV",
    menuAnalysisSample: "Analyze my menu analysis.\nItem: Chicken Biryani. Quantity Sold: 125. Price: $19.00. Cost: $6.20. Revenue: $2,375.00. Profit: $1,580.00. Category: Entrees. Food Cost %: 32.6%. Contribution Margin %: 67.4%.\nInclude: Sales mix analysis; Contribution margins; Menu matrix mapping.",
    menuPricingSample: "Analyze my pricing strategy.\nItem: Margherita Pizza. Item Price: $18.00. Item Cost: $5.50. Competitor Price: $16.00. Target Food Cost Percent: 32%. Elasticity Index: 1.2. Category: Pizza.\nFocus on: Price elasticity; Competitive analysis; Profit maximization.",
    menuOptimizationSample: "Analyze my item optimization.\nItem: Veggie Wrap. Quantity Sold: 12. Item Cost: $3.50. Portion Size: 220g. Portion Cost: $1.20. Waste Percent: 8%. Recipe Ingredients: Spinach wrap; seasonal vegetables; dressing. Description: Fresh seasonal vegetables in a spinach wrap.\nInclude: Recipe costing; Portion control; Description optimization.",

    // Recipe Intelligence Page
    recipeIntelligenceTitle: "Recipe Intelligence",
    recipeIntelligenceSubtitle:
      "Master your recipe costs and ingredient efficiency with precision\ncosting, optimization strategies, and scaling solutions.",
    createRecipe: "Create Recipe",
    ingredientSuggestion: "Ingredient suggestion",
    autoCosting: "Auto-costing",
    nutritionAnalysis: "Nutrition analysis",
    costAnalysis: "Cost Analysis",
    ingredientCostsTracking: "Ingredient costs tracking",
    marginCalculator: "Margin calculator",
    priceRecommendations: "Price recommendations",
    scaleRecipes: "Scale Recipes",
    batchScaling: "Batch scaling",
    unitConversion: "Unit conversion",
    yieldOptimization: "Yield optimization",
    recipeInputPlaceholder:
      'Select a card to load a sample prompt, or type recipe details (recipe_name "My Dish", servings 4, ingredient_cost 12.00...)',
    recipeFooterHint:
      "Press Enter to send  Shift + Enter for new line   to upload CSV",
    recipeCreateSample: 'Create a recipe named: recipe_name "Grilled Salmon", servings 6, prep_time 20, cook_time 30, ingredients: Salmon 24 oz, Lemon 4 oz, Butter 2 oz, Garlic 1 oz, ingredient_cost 18.00, labor_cost 4.50, recipe_price 28.00. Include ingredient suggestions, brief steps, nutrition per serving, and auto-costing.',
    recipeCostSample: 'Analyze recipe costs of: recipe_name "Grilled Salmon", ingredient_cost 5.80, portion_cost 2.30, recipe_price 13.50, servings 2, labor_cost 3.50. Calculate food cost %, margin, and recommend price to hit 70% margin.',
    recipeScaleSample: 'Scale "Classic Tomato Soup" which serves 6 to 48 servings. Provide ingredient quantities, converted units, and suggested batch yields.',

    // Strategic Planning Page
    strategicPlanningTitle: "Strategic Planning",
    strategicPlanningSubtitle:
      "Drive long-term success with SWOT analysis, goal-setting,\nand growth strategies tailored to your business.",
    swotAnalysis: "SWOT Analysis",
    strengthsWeaknesses: "Strengths & weaknesses identification",
    marketOpportunities: "Market opportunities analysis",
    threatMitigation: "Threat mitigation strategies",
    businessGoals: "Business Goals",
    smartGoalSetting: "SMART goal setting",
    progressTracking: "Progress tracking",
    milestonePlanning: "Milestone planning",
    growthStrategy: "Growth Strategy",
    expansionPlanning: "Expansion planning",
    marketAnalysis: "Market analysis",
    revenueProjections: "Revenue projections",
    strategicInputPlaceholder:
      "Describe your SWOT, business goals, or growth strategy metrics ...",
    strategicFooterHint:
      "Press Enter to send  Shift + Enter for new line  paperclip to upload CSV",
    strategicSwotSample: "Analysis type: SWOT\nPerform SWOT analysis. Strengths: loyal customer base, prime location; Weaknesses: high labor cost, limited seating; Opportunities: catering, online ordering; Threats: new competitors, rising food costs.",
    strategicGoalsSample: "Analysis type: Business Goals\nAnalyze business goals. Revenue target: $1,200,000. Budget total: $250,000. Marketing spend: $60,000. Target ROI: 20%. Timeline: 12 months.",
    strategicGrowthSample: "Analysis type: Growth Strategy\nAnalyze growth strategy. Market size: $5,000,000. Market share: 3%. Competition level: 65%. Investment budget: $150,000. Target ROI: 18%.",

    // CSV KPI Dashboard
    kpiDashboard: "KPI Dashboard",
    kpiDashboardSubtitle:
      "Real-time performance metrics and analytics\n\nfor your restaurant operations",
    revenue: "Revenue",
    laborCostPercent: "Labor Cost %",
    foodCostPercent: "Food Cost %",
    primeCostPercent: "Prime Cost %",
    vsLastPeriod: "+12.5% vs last period",
    vsTarget: "+2.3% vs target",
    vsFoodTarget: "-1.8% vs target",
    onTarget: "On target",
    revenueTrend: "Revenue Trend",
    costDistribution: "Cost Distribution",
    weeklyPerformance: "Weekly Performance",
    kpiComparison: "KPI Comparison",
    aiInsights: "AI Insights",
    clear: "Clear",
    ask: "Ask",
    askAboutKpis: "Ask about your KPIs, or upload a CSV...",
    justNow: "Just now",
    welcomeMessage: `Welcome to your KPI Dashboard! <strong>To get comprehensive analysis, provide your data</strong>:<br/><br/>
<strong>📊 Comprehensive Analysis:</strong><br/>
• Required: total_sales, labor_cost, food_cost, prime_cost<br/>
• Optional: hours_worked, hourly_rate, previous_sales, target_margin<br/><br/>
<strong>🎯 Performance Optimization:</strong><br/>
• Required: current_performance, target_performance, optimization_potential, efficiency_score<br/><br/>
Example: "Run comprehensive analysis. Total sales: $50,000. Labor cost: $15,000. Food cost: $14,000. Prime cost: $29,000."`,

    // New Chat Page
    yourHospitalityAiAssistant: "Your Hospitality AI Assistant",
    newChatSubtitle:
      "Ask anything about restaurant KPIs, staffing, purchasing, menu\nengineering, beverage management, or financial strategy.",
    hrOptimizations: "HR Optimizations",
    newChatInputPlaceholder:
      "Ask me anything about your restaurant KPIs, staffing, food cost, beverage cost, or business strategy...",
    newChatFooterHint:
      "Press Enter to send, Shift + Enter for new line \u00a0·\u00a0 📎 Attach a CSV file for KPI analysis",
    uploadCsvForKpi: "Upload a CSV file for KPI analysis",

    // Chat History Page
    findYourChatHistory: "Find Your All Chat history here",
    beverageManagement: "Beverage Management",
    staffingOptimization: "Staffing Optimization",
    noChatHistoryFound: "No chat history found",
    deleteChatHistory: "Delete Chat History",
    deleteChatConfirm:
      "Are you sure you want to delete this chat? This action cannot be undone.",
    cancel: "Cancel",
    delete: "Delete",

    // Profile Page
    userProfileTitle: "User Profile",
    restaurantManager: "Restaurant Manager",
    contactInformation: "Contact Information",
    fullName: "Full Name",
    emailAddress: "Email Address",
    edit: "Edit",
    saveChanges: "Save Changes",
    privacyAndSecurity: "Privacy & Security",
    password: "Password",
    changePassword: "Change Password",
    newPassword: "New Password",
    enterNewPassword: "Enter new password",
    confirmNewPassword: "Confirm New Password",
    confirmPassword: "Confirm password",
    savePassword: "Save Password",
    appearance: "Appearance",
    accountDetails: "Account Details",
    memberSince: "Member Since",
    accountStatus: "Account Status",
    active: "Active",
    logOut: "Log Out",
    signedOutFromAllDevices: "You will be signed out from all devices",
    profileUpdated: "Profile Updated",
    contactInfoSaved: "Your contact information has been saved.",
    passwordChanged: "Password Changed",
    passwordUpdatedSuccessfully: "Your password has been updated successfully.",

    // CSV upload messages
    uploadedCsv: "📎 Uploaded CSV:",
    uploadedCsvs: "📎 Uploaded CSVs:",
    csvError: "❌ CSV Error:",
    serverError: "Sorry, I was unable to reach the server. Please make sure the backend is running and try again.",

    // Chart labels
    labor: "Labor",
    food: "Food",
    overhead: "Overhead",
    profit: "Profit",
    current: "Current",
    target: "Target",
    sales: "Sales",
    downloadPdf: "Download PDF",
    downloading: "Downloading...",
  },

  es: {
    // Sidebar
    hospitalityAi: "Hospitalidad IA",
    aiAssistantActive: "Asistente IA Activo",
    newChat: "Nuevo Chat",
    chatHistory: "Historial de Chat",
    seeAllHistory: "Ver todo el historial",
    features: "Características",
    kpiAnalysis: "Análisis de KPI",
    hrOptimization: "Optimización de RRHH",
    beverageInsights: "Análisis de Bebidas",
    menuEngineering: "Ingeniería de Menú",
    recipeIntelligence: "Inteligencia de Recetas",
    strategicPlanning: "Planificación Estratégica",
    csvKpiDashboard: "Panel CSV KPI",
    userProfile: "Perfil de Usuario",
    selectLanguage: "Seleccionar idioma",

    // Chat History
    chatHistoryTitle: "Tu Asistente de IA de Hostelería",
    chatHistorySubtitle: "Encuentra todo tu historial de chat aquí",
    allTypes: "Todos los tipos",
    titleAndDescription: "Título y descripción",
    date: "Fecha",
    noChatHistory: "No se encontró historial de chat",

    // Mobile Header
    dashboard: "Panel",

    // KPI Analysis Page
    kpiAnalysisTitle: "Análisis de KPI",
    kpiAnalysisSubtitle:
      "Analice el costo laboral, costo primo y rendimiento de ventas con\nbenchmarking y recomendaciones impulsadas por IA.",
    laborCostAnalysis: "Análisis de Costo Laboral",
    laborCostPercentage: "Porcentaje de costo laboral",
    overtimeTracking: "Seguimiento de horas extra",
    productivityMetrics: "Métricas de productividad",
    primeCostAnalysis: "Análisis de Costo Primo",
    primeCostPercentage: "Porcentaje de costo primo",
    targetBenchmarking: "Benchmarking objetivo",
    trendAnalysis: "Análisis de tendencias",
    salesPerformance: "Rendimiento de Ventas",
    salesPerLaborHour: "Ventas por hora laboral",
    revenueTrends: "Tendencias de ingresos",
    growthAnalysis: "Análisis de crecimiento",
    kpiInputPlaceholder:
      "Ingrese: Venta Total, Costo Laboral, Horas Trabajadas (ej., 10000, 3000, 120)",
    pressEnterToSend:
      "Presione Enter para enviar, Shift + Enter para nueva línea",
    error: "Error",
    kpiLaborSample: "Analizar mi costo laboral. Ventas totales: $50,000. Costo laboral: $15,000. Horas trabajadas: 800. Horas extras: 40. Cubiertos servidos: 2,000.",
    kpiPrimeSample: "Analizar mi costo primo. Ventas totales: $50,000. Costo laboral: $15,000. Costo de alimentos: $14,000. Cubiertos servidos: 2,000.",
    kpiSalesSample: "Analizar mi rendimiento de ventas. Ventas totales: $50,000. Costo laboral: $15,000. Costo de alimentos: $14,000. Horas trabajadas: 800. Ventas anteriores: $48,000. Cubiertos servidos: 2,000. Cheque promedio: $25.",

    // HR Optimization Page
    hrOptimizationTitle: "Optimización de RRHH",
    hrOptimizationSubtitle:
      "Optimice la gestión de su fuerza laboral con información impulsada por IA\npara retención, programación y seguimiento de rendimiento.",
    staffRetention: "Retención de Personal",
    turnoverAnalysis: "Análisis de rotación",
    retentionStrategies: "Estrategias de retención",
    costImpactAssessment: "Evaluación de impacto de costos",
    laborScheduling: "Programación Laboral",
    shiftOptimization: "Optimización de turnos",
    peakHourCoverage: "Cobertura de horas pico",
    overtimeManagement: "Gestión de horas extra",
    trainingPrograms: "Programas de Capacitación",
    onboardingOptimization: "Optimización de incorporación",
    skillDevelopment: "Desarrollo de habilidades",
    performanceTracking: "Seguimiento de rendimiento",
    hrInputPlaceholder:
      "Ingrese datos de RRHH como pares clave:valor (ej., turnover_rate: 45, industry_average: 70)",
    hrRetentionSample: "Ejemplo de retención de personal: turnover_rate: 0.45, industry_average: 0.70, department: Front of House, employee_count: 25",
    hrSchedulingSample: "Ejemplo de programación laboral: total_sales: 50000, labor_hours: 800, hourly_rate: 15, peak_hours: 200, date: 2026-02-01, department: Kitchen.",
    hrPerformanceSample: "Ejemplo de programas de formación: customer_satisfaction: 0.85, sales_performance: 0.95, efficiency_score: 0.80, attendance_rate: 0.92, employee name: Alex Rivera, department: Service",

    // Beverage Insights Page
    beverageInsightsTitle: "Análisis de Bebidas",
    beverageInsightsSubtitle:
      "Optimice sus operaciones de bar con análisis integral\npara costos de licor, gestión de inventario y estrategias de precios.",
    liquorCostAnalysis: "Análisis de Costo de Licor",
    varianceAnalysis: "Análisis de varianza",
    costPerOunceTracking: "Seguimiento de costo por onza",
    wasteIdentification: "Identificación de desperdicio",
    barInventoryManagement: "Gestión de Inventario de Bar",
    stockLevelTracking: "Seguimiento de nivel de stock",
    reorderOptimization: "Optimización de reorden",
    inventoryValuation: "Valuación de inventario",
    beveragePricing: "Precios de Bebidas",
    marginAnalysis: "Análisis de margen",
    competitivePricing: "Precios competitivos",
    profitOptimization: "Optimización de ganancias",
    beverageInputPlaceholder:
      "Ingrese: Ventas Totales de Bebidas, Costo de Bebidas, % de Costo de Vertido (ej., $50000, $12000, 24%)",
    bevLiquorSample: "Análisis de Costo de Licor:\nExpected oz: 1500, Actual oz: 1650, Liquor cost: $3500, Total sales: $15000, Bottle cost: $25, Bottle size oz: 25, Target cost percentage: 20%",
    bevBarSample: "Análisis de Inventario de Bar:\nCurrent stock: 800, Reorder point: 250, Monthly usage: 600, Inventory value: $12500, Lead time days: 7, Safety stock: 100, Item cost: $12.5, Target turnover: 12",
    bevPricingSample: "Análisis de Precios de Bebidas:\nDrink price: $12, Cost per drink: $3, Sales volume: 1800, Competitor price: $11, Target margin: 75%, Market position: premium, Elasticity factor: 1.5",

    // Menu Engineering Page
    menuAnalysisTitle: "Análisis de Menú",
    salesMixAnalysis: "Análisis de mezcla de ventas",
    contributionMargins: "Márgenes de contribución",
    menuMatrixMapping: "Mapeo de matriz de menú",
    pricingStrategyTitle: "Estrategia de Precios",
    priceElasticity: "Elasticidad precio",
    competitiveAnalysis: "Análisis competitivo",
    profitMaximization: "Maximización de ganancias",
    itemOptimizationTitle: "Optimización de Artículos",
    recipeCosting: "Costeo de recetas",
    portionControl: "Control de porciones",
    descriptionOptimization: "Optimización de descripciones",
    menuEngineeringSubtitle: "Transforme su menú en un generador de ganancias con información basada en datos\nsobre mezcla de productos, estrategias de precios y optimización de diseño.",
    menuInputPlaceholder: "Seleccione una tarjeta para cargar un ejemplo, o escriba detalles del artículo del menú...",
    menuFooterHint: "Presione Enter para enviar  Shift + Enter para nueva línea   para subir CSV",
    menuAnalysisSample: "Analizar el análisis de mi menú.\nItem: Chicken Biryani. Quantity Sold: 125. Price: $19.00. Cost: $6.20. Revenue: $2,375.00. Profit: $1,580.00. Category: Entrees. Food Cost %: 32.6%. Contribution Margin %: 67.4%.\nInclude: Sales mix analysis; Contribution margins; Menu matrix mapping.",
    menuPricingSample: "Analizar mi estrategia de precios.\nItem: Margherita Pizza. Item Price: $18.00. Item Cost: $5.50. Competitor Price: $16.00. Target Food Cost Percent: 32%. Elasticity Index: 1.2. Category: Pizza.\nFocus on: Price elasticity; Competitive analysis; Profit maximization.",
    menuOptimizationSample: "Analizar la optimización de mis artículos.\nItem: Veggie Wrap. Quantity Sold: 12. Item Cost: $3.50. Portion Size: 220g. Portion Cost: $1.20. Waste Percent: 8%. Recipe Ingredients: Spinach wrap; seasonal vegetables; dressing. Description: Fresh seasonal vegetables in a spinach wrap.\nInclude: Recipe costing; Portion control; Description optimization.",

    // Recipe Intelligence Page
    recipeIntelligenceTitle: "Inteligencia de Recetas",
    recipeIntelligenceSubtitle:
      "Domine los costos de sus recetas y la eficiencia de ingredientes con\ncosteo preciso, estrategias de optimización y soluciones de escalado.",
    createRecipe: "Crear Receta",
    ingredientSuggestion: "Sugerencia de ingredientes",
    autoCosting: "Costeo automático",
    nutritionAnalysis: "Análisis nutricional",
    costAnalysis: "Análisis de Costos",
    ingredientCostsTracking: "Seguimiento de costos de ingredientes",
    marginCalculator: "Calculadora de margen",
    priceRecommendations: "Recomendaciones de precios",
    scaleRecipes: "Escalar Recetas",
    batchScaling: "Escalado por lotes",
    unitConversion: "Conversión de unidades",
    yieldOptimization: "Optimización de rendimiento",
    recipeInputPlaceholder:
      'Seleccione una tarjeta para cargar un ejemplo, o escriba detalles de receta (recipe_name "Mi Plato", servings 4, ingredient_cost 12.00...)',
    recipeFooterHint:
      "Presione Enter para enviar  Shift + Enter para nueva línea   para subir CSV",
    recipeCreateSample: 'Crear una receta llamada: recipe_name "Salmón a la Parrilla", servings 6, prep_time 20, cook_time 30, ingredients: Salmón 24 oz, Limón 4 oz, Mantequilla 2 oz, Ajo 1 oz, ingredient_cost 18.00, labor_cost 4.50, recipe_price 28.00. Incluir sugerencias de ingredientes, pasos breves, nutrición por porción y costeo automático.',
    recipeCostSample: 'Analizar costos de la receta: recipe_name "Salmón a la Parrilla", ingredient_cost 5.80, portion_cost 2.30, recipe_price 13.50, servings 2, labor_cost 3.50. Calcular % de costo de alimentos, margen y recomendar precio para alcanzar el 70% de margen.',
    recipeScaleSample: 'Escalar "Sopa de Tomate Clásica" de 6 a 48 porciones. Proporcionar cantidades de ingredientes, unidades convertidas y rendimiento sugerido del lote.',

    // Strategic Planning Page
    strategicPlanningTitle: "Planificación Estratégica",
    strategicPlanningSubtitle:
      "Impulse el éxito a largo plazo con análisis FODA, establecimiento de metas\ny estrategias de crecimiento adaptadas a su negocio.",
    swotAnalysis: "Análisis FODA",
    strengthsWeaknesses: "Identificación de fortalezas y debilidades",
    marketOpportunities: "Análisis de oportunidades de mercado",
    threatMitigation: "Estrategias de mitigación de amenazas",
    businessGoals: "Metas de Negocio",
    smartGoalSetting: "Establecimiento de metas SMART",
    progressTracking: "Seguimiento de progreso",
    milestonePlanning: "Planificación de hitos",
    growthStrategy: "Estrategia de Crecimiento",
    expansionPlanning: "Planificación de expansión",
    marketAnalysis: "Análisis de mercado",
    revenueProjections: "Proyecciones de ingresos",
    strategicInputPlaceholder:
      "Describa su FODA, metas de negocio o métricas de estrategia de crecimiento ...",
    strategicFooterHint:
      "Presione Enter para enviar  Shift + Enter para nueva línea  clip para subir CSV",
    strategicSwotSample: "Tipo de análisis: FODA\nRealizar análisis FODA. Fortalezas: base de clientes leales, ubicación privilegiada; Debilidades: alto costo laboral, asientos limitados; Oportunidades: catering, pedidos en línea; Amenazas: nuevos competidores, aumento de costos de alimentos.",
    strategicGoalsSample: "Tipo de análisis: Metas de Negocio\nAnalizar metas de negocio. Revenue target: $1,200,000. Budget total: $250,000. Marketing spend: $60,000. Target ROI: 20%. Timeline: 12 meses.",
    strategicGrowthSample: "Tipo de análisis: Estrategia de Crecimiento\nAnalizar estrategia de crecimiento. Market size: $5,000,000. Market share: 3%. Competition level: 65%. Investment budget: $150,000. Target ROI: 18%.",

    // CSV KPI Dashboard
    kpiDashboard: "Panel de KPI",
    kpiDashboardSubtitle:
      "Métricas de rendimiento en tiempo real y análisis\n\npara las operaciones de su restaurante",
    revenue: "Ingresos",
    laborCostPercent: "Costo Laboral %",
    foodCostPercent: "Costo de Alimentos %",
    primeCostPercent: "Costo Primo %",
    vsLastPeriod: "+12.5% vs período anterior",
    vsTarget: "+2.3% vs objetivo",
    vsFoodTarget: "-1.8% vs objetivo",
    onTarget: "En objetivo",
    revenueTrend: "Tendencia de Ingresos",
    costDistribution: "Distribución de Costos",
    weeklyPerformance: "Rendimiento Semanal",
    kpiComparison: "Comparación de KPI",
    aiInsights: "Análisis IA",
    clear: "Limpiar",
    ask: "Preguntar",
    askAboutKpis: "Pregunte sobre sus KPIs, o suba un CSV...",
    justNow: "Justo ahora",
    welcomeMessage: `¡Bienvenido a su Panel de KPI! <strong>Para obtener un análisis completo, proporcione sus datos</strong>:<br/><br/>
<strong>📊 Análisis Completo:</strong><br/>
• Requerido: total_sales, labor_cost, food_cost, prime_cost<br/>
• Opcional: hours_worked, hourly_rate, previous_sales, target_margin<br/><br/>
<strong>🎯 Optimización de Rendimiento:</strong><br/>
• Requerido: current_performance, target_performance, optimization_potential, efficiency_score<br/><br/>
Ejemplo: "Run comprehensive analysis. Total sales: $50,000. Labor cost: $15,000. Food cost: $14,000. Prime cost: $29,000."`,

    // New Chat Page
    yourHospitalityAiAssistant: "Su Asistente de Hospitalidad IA",
    newChatSubtitle:
      "Pregunte cualquier cosa sobre KPIs de restaurante, personal, compras, ingeniería\nde menú, gestión de bebidas o estrategia financiera.",
    hrOptimizations: "Optimizaciones de RRHH",
    newChatInputPlaceholder:
      "Pregúnteme cualquier cosa sobre los KPIs de su restaurante, personal, costo de alimentos, costo de bebidas o estrategia comercial...",
    newChatFooterHint:
      "Presione Enter para enviar, Shift + Enter para nueva línea \u00a0·\u00a0 📎 Adjunte un archivo CSV para análisis de KPI",
    uploadCsvForKpi: "Subir un archivo CSV para análisis de KPI",

    // Chat History Page
    findYourChatHistory: "Encuentre todo su historial de chat aquí",
    beverageManagement: "Gestión de Bebidas",
    staffingOptimization: "Optimización de Personal",
    noChatHistoryFound: "No se encontró historial de chat",
    deleteChatHistory: "Eliminar Historial de Chat",
    deleteChatConfirm:
      "¿Está seguro de que desea eliminar este chat? Esta acción no se puede deshacer.",
    cancel: "Cancelar",
    delete: "Eliminar",

    // Profile Page
    userProfileTitle: "Perfil de Usuario",
    restaurantManager: "Gerente de Restaurante",
    contactInformation: "Información de Contacto",
    fullName: "Nombre Completo",
    emailAddress: "Correo Electrónico",
    edit: "Editar",
    saveChanges: "Guardar Cambios",
    privacyAndSecurity: "Privacidad y Seguridad",
    password: "Contraseña",
    changePassword: "Cambiar Contraseña",
    newPassword: "Nueva Contraseña",
    enterNewPassword: "Ingrese nueva contraseña",
    confirmNewPassword: "Confirmar Nueva Contraseña",
    confirmPassword: "Confirmar contraseña",
    savePassword: "Guardar Contraseña",
    appearance: "Apariencia",
    accountDetails: "Detalles de Cuenta",
    memberSince: "Miembro Desde",
    accountStatus: "Estado de Cuenta",
    active: "Activo",
    logOut: "Cerrar Sesión",
    signedOutFromAllDevices:
      "Se cerrará la sesión en todos los dispositivos",
    profileUpdated: "Perfil Actualizado",
    contactInfoSaved: "Su información de contacto ha sido guardada.",
    passwordChanged: "Contraseña Cambiada",
    passwordUpdatedSuccessfully:
      "Su contraseña ha sido actualizada exitosamente.",

    // CSV upload messages
    uploadedCsv: "📎 CSV subido:",
    uploadedCsvs: "📎 CSVs subidos:",
    csvError: "❌ Error de CSV:",
    serverError: "Lo siento, no pude conectarme al servidor. Asegúrese de que el backend esté ejecutándose e intente de nuevo.",

    // Chart labels
    labor: "Laboral",
    food: "Alimentos",
    overhead: "Gastos Generales",
    profit: "Ganancia",
    current: "Actual",
    target: "Objetivo",
    sales: "Ventas",
    downloadPdf: "Descargar PDF",
    downloading: "Descargando...",
  },
} as const;

export type TranslationKey = keyof typeof translations.en;
