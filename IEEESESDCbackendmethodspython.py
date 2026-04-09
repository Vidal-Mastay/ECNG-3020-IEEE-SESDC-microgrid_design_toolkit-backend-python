import numpy as np
import cvxpy as cp
import pandas as pd
from pandas.errors import ParserError, EmptyDataError

class DataRead:
    def __init__(self):                 # intilises variables to be used by the class.Some variables are used in the optimisation class(inheritance)
        self.CSV_file=None
        self.PV_index=None
        self.WT_index=None
        self.DG_index=None
        self.INV_index=None
        self.BAT_index=None
        self.PV_cc_index=None
        self.WT_cc_index=None
        self.DG_cc_index=None
        self.model_unit_cost=None
        self.model_power_rating=None
        self.rated_lifetime=None
        self.model_unit_area=None
        self.labour_cost=None
        self.maintenance_factor=None
        self.model_maintenance_cost=None
        self.number_of_components=None
        self.number_of_models=None
        self.model_effective_power=None
        self.model_effective_lifetime=None
        self.intercomponent_constraints={}


    def whitespace_remover(self,data_frame): 
        
        """ function removes whitespace from csv (Geeksforgeeks,2025)
            :data_frame: Acts on the dataframe accepted
            :returns nothing
        """
        for i in data_frame.columns:
            if data_frame[i].dtype== 'object':
             data_frame[i]=data_frame[i].map(str.strip)
        else:
            pass

    def find_model(self,model_name, data_frame): 
        """ find the index for a given model name
            :model_name String parameter of model choosen
            :data_frame: Acts on the dataframe accepted
            :returns nothing
        """
        if model_name not in data_frame['Model name'].values:
            return None
        return data_frame[data_frame['Model name'] == model_name].index

    def read_in_data(self,path):     
        """
        Reads data for a csv and sets up required matrices and indicies.
        :path: Uses a selected path to accept data in the format of a csv
        returns nothing
        """
        try:
            CSV_file = pd.read_csv(path)
        except FileNotFoundError:
             print("The file could not be found.")
        except EmptyDataError:
            print("File is empty.")
        except ParserError:
            print("The file could not be parsed.")
        except Exception as f:
            print(f"An unexpected error occurred: {f}")
            
        self.whitespace_remover(CSV_file)
        Components=CSV_file['Component type'].unique()#sets the variable to store the different component types 
        counter=CSV_file['Component type'].value_counts()  #Counts the different component types 
        self.number_of_components = Components.size #Sets the number of components 
        self.number_of_models = counter.iloc[0]  # sets the max number of models(columns)
        CostMaximisation=1e9 #variable to call to set costs extremely high
        max_derating_value=0.99
        for C in Components:    #checking all components
            if counter.loc[C]<self.number_of_models:   #if a component has less models than the the component check the difference
                difference=self.number_of_models-counter.loc[C] #difference here
                for i in range(difference): #for all the missing elements set dummy data so the optimisier never considers it 
                    DummyComponent=pd.DataFrame({
                        'Model name'     : '',
                        'Component type': C,

                        # Costs set to very high (max)
                        'Unit cost'    : CostMaximisation,
                        'Labour cost'  : CostMaximisation,
                        'Omcost'       : CostMaximisation,

                        # Performance set to very low (min)
                        'Rated Power'  : 0.0,
                        'Rated lifetime': 0.1,   #minimum non-zero lifetime
                        'Area of model': 1e6,    #large area to penalise area constraint

                        #Power output derating (worst case)
                        'DustP'     : max_derating_value,
                        'WindP'     : max_derating_value,
                        'SolarP'    : max_derating_value,          
                        'HumidityP': max_derating_value,

                        #Lifetime derating factors (worst case)
                        'DustL'     : max_derating_value,
                        'WindL'     : max_derating_value,
                        'SolarL'    : max_derating_value,
                        'HumidityL': max_derating_value,
                        'Maintenance' :max_derating_value },index=[0])
                    CSV_file=pd.concat([CSV_file,DummyComponent],ignore_index=True)# inserts dummy row into dataframe
                    
        CSV_file=CSV_file.sort_values(by=['Component type','Model name'])#sort by components in alphabetical order in the data frame

        sorted_components = CSV_file['Component type'].unique() #store all the unique components 
       
        (PV, WT, DG, INV, BAT, PVCC, WTCC, DGCC) = (      #Assigns the sorted data to these variables for simplicity (simplifies the use of indexing )
            np.where(sorted_components == 'PV')[0][0], 
            np.where(sorted_components == 'Wind turbine')[0][0], 
            np.where(sorted_components == 'Diesel Generator')[0][0], 
            np.where(sorted_components == 'Inverter')[0][0], 
            np.where(sorted_components == 'Energy storage')[0][0], 
            np.where(sorted_components == 'Solar Power management')[0][0],
            np.where(sorted_components == 'Wind Power management')[0][0],
            np.where(sorted_components == 'Generator Power management')[0][0])

        self.intercomponent_constraints={           #Dictionary that is used to relax intercomponent behaviour(maps indicies between related components)    
            PV:[INV,BAT,PVCC],
            WT:[BAT,WTCC],
            DG:[BAT,DGCC],
            INV:[BAT,PV,PVCC],
            PVCC:[BAT,PV,INV],
            WTCC:[BAT,WT],
            DGCC:[BAT,DG],
            BAT:[PVCC,WTCC,DGCC,INV]
            }
        
        #Read in the model parameters from the csv and form the respective matrices for each parameter

        self.model_unit_cost=CSV_file['Unit cost'].to_numpy().reshape(self.number_of_components,self.number_of_models)
        self.model_power_rating=CSV_file['Rated Power'].to_numpy().reshape(self.number_of_components,self.number_of_models)
        self.rated_lifetime=CSV_file['Rated lifetime'].to_numpy().reshape(self.number_of_components,self.number_of_models)
        self.model_unit_area=CSV_file['Area of model'].to_numpy().reshape(self.number_of_components,self.number_of_models)
        
        solar_irradiance_power_derating=CSV_file['SolarP'].to_numpy().reshape(self.number_of_components,self.number_of_models)
        wind_speed_power_derating=CSV_file['WindP'].to_numpy().reshape(self.number_of_components,self.number_of_models)
        dust_power_derating=CSV_file['DustP'].to_numpy().reshape(self.number_of_components,self.number_of_models)
        humidity_power_derating=CSV_file['HumidityP'].to_numpy().reshape(self.number_of_components,self.number_of_models)
        solar_irradiance_lifetime_derating=CSV_file['SolarL'].to_numpy().reshape(self.number_of_components,self.number_of_models)
        wind_speed_lifetime_derating=CSV_file['WindL'].to_numpy().reshape(self.number_of_components,self.number_of_models)
        dust_lifetime_derating=CSV_file['DustL'].to_numpy().reshape(self.number_of_components,self.number_of_models)
        humidity_lifetime_derating=CSV_file['HumidityL'].to_numpy().reshape(self.number_of_components,self.number_of_models)
        
        self.labour_cost=CSV_file['Labour cost'].to_numpy().reshape(self.number_of_components,self.number_of_models)
        self.maintenance_factor=CSV_file['Maintenance'].to_numpy().reshape(self.number_of_components,self.number_of_models)
        self.model_maintenance_cost=CSV_file['Omcost'].to_numpy().reshape(self.number_of_components,self.number_of_models)

        power_derating_values_=(1-solar_irradiance_power_derating)*(1-wind_speed_power_derating)*(1-dust_power_derating)*(1-humidity_power_derating) #aggregrate derating effects for each model with respect to rated output  
        self.model_effective_power=self.model_power_rating*power_derating_values_ #apply aggregrated derating effects to the rated power values 

        lifetime_derating_values=(1-solar_irradiance_lifetime_derating)*(1-wind_speed_lifetime_derating)*(1-dust_lifetime_derating)*(1-humidity_lifetime_derating) #aggregrate derating effects for each model with respect to rated lifetime
        self.model_effective_lifetime=self.rated_lifetime*lifetime_derating_values*(1+self.maintenance_factor) #apply aggregrated derating effects to the rated lifetime 

        #Assigns all variables used to their instance variables for future use in other methods 
        self.CSV_file=CSV_file
        self.PV_index=PV
        self.WT_index=WT
        self.DG_index=DG
        self.INV_index=INV
        self.BAT_index=BAT
        self.PV_cc_index=PVCC
        self.WT_cc_index=WTCC
        self.DG_cc_index=DGCC
        

class Optimisation(DataRead):  #Optimisation occurs in a seperate class using inherited parameters from  (Allows matrices from DataRead to be used in optimisation class and methods)

    def __init__(self): #initialises instance variables
        super().__init__()
        self.optimal_solution=None
        self.solution_area_required=None
        self.area_limit=None
        self.area_slack=None
        self.component_capex=None
        self.labour_capex=None
        self.replacement_units=None
        self.replacement_cost=None
        self.om_total_cost=None
        self.total_fuel_cost=None
        self.goal=None
        self.answer=None
        self.base_constraints=[]
        self.additional_constraints=[]
        self.area_constraint=None
        self.model_dict={}
        

    def solution_setup(self,project_lifetime,peak_load_demand,battery_decision,BatteryCapacity,area_limit,fuel_capacity_value,Heatrate,fuel_cost):  
        """
        Accepts parameters to be used in developed expressions for Optimisation and uses accepted parameter in conjuction with earlier developed matrices to form expressions to 
        be used by the optimiser for constraint modeling and to determine the final CAPEX and OPEX.

        :project_lifetime: Expected lifetime of the solution. Used to determine component choice and whether replacements are required.
        :peak_load_demand:The real powerload required to be satisfied by the solution
        :battery_decision: Used to determine whether battery is part of the solution.
        :BatteryCapacity: The required capacity that must be satisfied by the chosen batteries 
        :area_limit: The area in metres^2 that the solution cannot exceed
        :fuel_capacity_value: Used to set an aggregated amount of energy utlised by generator
        :Heatrate:The heatrate of the fuel
        :fuel_cost The cost of fuel 

        Returns nothing
        """
        if(project_lifetime<0 or peak_load_demand<0 or BatteryCapacity<0 or area_limit<0 or fuel_capacity_value<0 or Heatrate<0 or fuel_cost<0):
            print('Error. Ensure all inputs are nonnegative')   #Cannot have negative power,years,area etc.
            return
        if(battery_decision>1 or battery_decision<0):
            print('Incorrect decision identifier use either 1 or 0')
            return
        #Assigns some of the accepted paramters to their instance method versions to be resused in different functions
        self.project_lifetime=project_lifetime
        self.area_limit=area_limit
        Replacement_count=(np.floor_divide(self.project_lifetime,self.model_effective_lifetime))
        #Setting up CVXPY variables 
        self.optimal_solution=cp.Variable((self.number_of_components,self.number_of_models),nonneg=True,integer=True)

        #CAPEX
        self.component_capex=cp.sum(cp.multiply(self.optimal_solution,self.model_unit_cost)) #Expression for component CAPEX
        self.labour_capex=cp.sum(cp.multiply(self.optimal_solution,self.labour_cost))#Expression for labour CAPEX
        CAPEX=self.component_capex+self.labour_capex #Total CAPEX

        #OPEX
        self.om_total_cost=cp.sum(cp.multiply(self.optimal_solution,self.model_maintenance_cost))*self.project_lifetime #Expression for operational and maintenance cost
        diesel_power=cp.sum(cp.multiply(self.optimal_solution[self.DG_index,:],self.model_effective_power[self.DG_index,:]))  #Expression for the power generated by Diesel generators
        diesel_energy=diesel_power*8760*self.project_lifetime*(fuel_capacity_value/1000)
        self.total_fuel_cost=diesel_energy*Heatrate*fuel_cost

        #Replacement
        self.replacement_units=cp.multiply(self.optimal_solution,Replacement_count)
        self.replacement_cost=cp.sum(cp.multiply(self.replacement_units,(self.model_unit_cost+self.labour_cost)))
        OPEX=self.om_total_cost+self.total_fuel_cost+self.replacement_cost #Total OPEX

        #Constraints 
        #Area constraints 
        self.solution_area_required=cp.sum(cp.multiply(self.optimal_solution[self.PV_index,:],self.model_unit_area[self.PV_index,:]))+\
                        cp.sum(cp.multiply(self.optimal_solution[self.WT_index,:],self.model_unit_area[self.WT_index,:]))+\
                        cp.sum(cp.multiply(self.optimal_solution[self.DG_index,:],self.model_unit_area[self.DG_index,:]))
        self.area_constraint=self.solution_area_required<=area_limit

        #Load constraints 
        PV_power=cp.sum(cp.multiply(self.optimal_solution[self.PV_index,:],self.model_effective_power[self.PV_index,:]))
        WT_power=cp.sum(cp.multiply(self.optimal_solution[self.WT_index,:],self.model_effective_power[self.WT_index,:]))
        DG_power=cp.sum(cp.multiply(self.optimal_solution[self.DG_index,:],self.model_effective_power[self.DG_index,:]))

        Required_load=PV_power+WT_power+DG_power

        #inverter constraints 
        Inverter_size=cp.sum(cp.multiply(self.optimal_solution[self.INV_index,:],self.model_power_rating[self.INV_index,:]))
        Inverter_limit=(cp.sum(1.3*(cp.multiply(self.optimal_solution[self.PV_index,:],self.model_effective_power[self.PV_index,:]))))

        #Battery constraints if user requests battery storage 
        if battery_decision==1:
           
            Battery_size=cp.sum(cp.multiply(self.optimal_solution[self.BAT_index,:],self.model_effective_power[self.BAT_index,:]))
            

            DG_charge_controller_limit=cp.sum(cp.multiply(self.optimal_solution[self.DG_index,:],self.model_effective_power[self.DG_index,:]))
            PV_charge_controller_limit=cp.sum(cp.multiply(self.optimal_solution[self.PV_index,:],self.model_effective_power[self.PV_index,:]))
            WT_charge_controller_limit=cp.sum(cp.multiply(self.optimal_solution[self.WT_index,:],self.model_effective_power[self.WT_index,:]))

            PV_charge_controller_size=cp.sum(cp.multiply(self.optimal_solution[self.PV_cc_index,:],self.model_effective_power[self.PV_cc_index,:]))
            WT_charge_controller_size=cp.sum(cp.multiply(self.optimal_solution[self.WT_cc_index,:],self.model_effective_power[self.WT_cc_index,:]))
            DG_charge_controller_size=cp.sum(cp.multiply(self.optimal_solution[self.DG_cc_index,:],self.model_effective_power[self.DG_cc_index,:]))

            self.base_constraints=[Required_load>=peak_load_demand,
                    Inverter_size>=Inverter_limit,
                    self.area_constraint,
                    Battery_size>=BatteryCapacity,
                    PV_charge_controller_size>=PV_charge_controller_limit,
                    WT_charge_controller_size>=WT_charge_controller_limit,
                    DG_charge_controller_size>=DG_charge_controller_limit]
        #Constraints if the user does not want battery storage 
        else:
            self.base_constraints=[Required_load>=peak_load_demand,Inverter_size>=Inverter_limit,self.area_constraint]
        self.goal=(CAPEX+OPEX)
                                                         
    # Two methods one for solving and one for setting up return the expression from set up to be passed to answer
    def Solving(self):
            """
            Solving does the actual calculations of the given problem and constraints.Done seperately to allow the other methods to append to constraints allowing solution to be
            repeatedly solved
            returns nothing
            """
            constraints=self.base_constraints+self.additional_constraints
            #Solving
            self.answer=cp.Problem(cp.Minimize(self.goal),constraints)
            self.answer.solve(solver=cp.HIGHS)  
            if self.optimal_solution.value is None:
             print('The solution is infeasible. Most likely due to Area/power generation violation \n ')
             return
            
    def clear_added_constraints(self): 
        """
        Clears the appended constraints. Used to reset appended constraints from other methods. Used to reset back to the intial solution.
        Returns nothing
        """
        self.additional_constraints.clear()

    def component_list(self):# Is used to obtain results from the given solution.
        """
        Used to set a list of chosen model and components.
        Appends two lists: the chosen models and the required amount of replacements
        Returns the lists
        """
        list_of_choosen_models=[]
        list_of_replacements=[]
        if self.optimal_solution.value is None:
             print('The solution is infeasible. Most likely due to Area/power generation violation \n ')
             return
        check=np.where(self.optimal_solution.value>0)   #checks the solution matrix to determine chosen models and components
        checkr=np.where(self.replacement_units.value>0)  #checks the replacement matrix to determine which components need to be replaced
        
        for row,column in zip(check[0],check[1]): #forms a tuple using the first two values from the check, this is the coordinates for the models and components choosen 
            label=self.CSV_file['Model name'].iloc[self.number_of_models*row + column]   #finds the label of this model at this location
            choosen_quantity=round(self.optimal_solution.value[row][column])      #finds the quantity 
            list_of_choosen_models.append({ 'model name':label,'count':choosen_quantity})#appends the label and quantity to a list

        for row,column in zip(checkr[0],checkr[1]):
            label=self.CSV_file['Model name'].iloc[self.number_of_models*row + column]
            choosen_replacements=round(self.replacement_units.value[row][column])
            list_of_replacements.append({ 'model name':label,'count':choosen_replacements})     #Same logic implemented for replacement count matrix 
        return list_of_choosen_models,list_of_replacements
     

    def omit_generation(self,generation_type): #this function is used to ban a type of generation after obtaining the initial solution.
        """
        Used to ban types of generation from the initial given solution
        :generation_type: the index of the choosen generation type 
        Appends the banned generation type as a constraint.
        returns nothing
        """
        self.area_slack=cp.Variable(nonneg=True)
        self.base_constraints.remove(self.area_constraint)
        self.area_constraint=self.solution_area_required<=self.area_limit+self.area_slack
        self.base_constraints.append(self.area_constraint)      # Accounts for area slack if new solution exceeds initial area
        generation_list=[self.PV_index,self.WT_index,self.DG_index]
        if generation_type not in generation_list:
             print('Please only select a type of generation')
             return
        x=cp.sum(self.optimal_solution[generation_type,:])==0 #constraints the chosen type of generation to 0
        self.additional_constraints.append(x)#append(use solving after to see new solution)

    def model_variation(self,model_choice):
        """
        Used to choose a specific model from the chosen component types after the intial solution. Constrains the other models of the same type of the choice to 0
        Constrains the component types of the model that was not chosen to their intial values.
        Allows component types that are related to the chosen model to change freely by use of the class dictionary Intercomponent_constraints
        :model_choice: String of the choosen model
        returns nothing
        """
        self.area_slack=cp.Variable(nonneg=True)
        self.base_constraints.remove(self.area_constraint)
        self.area_constraint=self.solution_area_required<=self.area_limit+self.area_slack
        self.base_constraints.append(self.area_constraint) # Accounts for area slack if new solution exceeds initial area
        model_index=self.find_model(model_choice,self.CSV_file)
        if model_index is None:
            print('Model could not be found. Please try again:\n')
            return
        model_pos=self.CSV_file.index.get_loc(model_index[0])        #Gets the position of the model in order of the sorted dataframe
        model_row,model_col=divmod(model_pos,self.number_of_models) #Since we know the dimensions of the matrix are mapped to the order of the sorted dataframe div mod returns the row and column 
        self.model_dict[model_row]=model_col    #creates a kay value pair in the dictionary indicating the specific model (the column) of the specifc type (row) that is being selected
        for i in range (self.number_of_components): 
            for j in range (self.number_of_models):#iterates through the row and column for every cell in the matrix.Then does the constraint appending stated in the docstring.
                if i in self.model_dict:
                    if j != self.model_dict[i]:
                        self.additional_constraints.append(self.optimal_solution[i][j]==0)
                        self.additional_constraints.append(self.replacement_units[i][j]==0)
                elif i in self.intercomponent_constraints[model_row]:#used the intercomponent dictionary to relax constraints
                    pass
                else:
                    self.additional_constraints.append(self.optimal_solution[i][j]==self.optimal_solution.value[i][j])  
                    self.additional_constraints.append(self.replacement_units[i][j]==self.replacement_units.value[i][j])\
                    





 
