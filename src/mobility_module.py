# Importing NumPy for numerical operations.
import numpy as np

# Importing pandas for data manipulation and analysis.
import pandas as pd

# Importing matplotlib for plotting and visualization.
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.ticker import LinearLocator

# Importing scipy for scientific computing and optimization.
from scipy.optimize import fsolve

# Importing Plotly for interactive plotting.
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def linspace_creator(max_value_array, min_value, res):
    """
    creates a linsapce numpy array from the given inputs
    max_value needs to be a numpy array (even if it is a 1x1)
    min value is to be an int or float
    resolution to be an int
    returns
    res = resoltuion, also used as a flag to set minimum/maxmum single load scearios
    Output is an N1 * N2 matrix where N1 = the number of hpvs and N2 = the resolution.
    """
    if res == 1:  # if res =1 , calculate for max load of HPV
        load_matrix = np.zeros((len(max_value_array), res))  # initilaise numpy matrix
        load_matrix = max_value_array
    elif (
        res == 0
    ):  # if res =0 , calculate for min viable load of HPV (trick: use this to set custom load)
        load_matrix = (
            np.zeros((len(max_value_array), 1)) + min_value
        )  # initilaise numpy matrix
        load_matrix = load_matrix
    elif res > 1:
        load_matrix = np.zeros(
            (len(max_value_array), res)
        )  # initilaise numpy matrix, numbers of rows = hpvs, cols = resolution

        #### Create linear space of weights
        # creates a vector for each of the HPVs, an equal number of elements spaced
        # evenly between the minimum viable load and the maximum load for that HPV
        i = 0  # initliase index
        for maxval in np.nditer(max_value_array):  # iterate through numpy array
            minval = min_value
            load_vector = np.linspace(
                start=minval,  # define linear space of weights
                stop=maxval,  # define maximum value for linear space
                num=res,  # how many data points?
                endpoint=True,
                retstep=False,
                dtype=None,
            )
            load_matrix[i:] = load_vector  # place the vector in to a matrix
            i += 1  # increment index
    else:
        print("Error: unexpected loading resolution, setting default")
        load_matrix = max_value_array

    return load_matrix


def max_safe_load(m_HPV_only, LoadCapacity, F_max, s, g):
    max_load_HPV = LoadCapacity
    """
    #### Weight limits
    Takes in the mass of the HPV (array), the load capacity of the HPV (array), max force that a person can push up a hill, the slope, and gravity
    # Calculate weight limits for hills. There are some heavy loads which humans will not be able to push up certain hills
    # Note that this is for average slopes etc. This will be innacurate (i.e one VERY hilly section could render the whole thing impossible, this isn't accounted for here)
    """
    if s != 0:  # requires check to avoid divide by zero
        max_pushable_weight = F_max / (np.sin(s) * g)
        i = 0
        if m_HPV_only.size > 1:  # can't iterate if there is only a float (not an array)
            for HPV_weight in m_HPV_only:
                if max_load_HPV[i] + HPV_weight > max_pushable_weight:
                    max_load_HPV[i] = max_pushable_weight - HPV_weight
                i += 1
        else:
            max_load_HPV = max_pushable_weight - m_HPV_only

    return max_load_HPV


class mobility_models:

    def bike_power_solution(p, *data):
        ro, C_d, A, m_t, Crr, eta, P_t, g, s = data
        v_solve = p[0]
        return (
            1 / 2 * ro * v_solve**3 * C_d * A
            + v_solve * m_t * g * Crr
            + v_solve * m_t * g * s
        ) / eta - P_t

    def single_lankford_run(mv, mo, met, hpv, slope, load_attempted):
        """
        Perform a single run of the Lankford model for a given HPV, slope, and load.

        Args:
            mv: Model variables
            mo: Model options
            met: Metabolic values
            hpv: HPV variables
            slope: Slope of the terrain
            load_attempted: Load attempted to be carried

        Returns:
            loaded_velocity: Velocity with load
            unloaded_velocity: Velocity without load
            max_load_HPV: Maximum load the HPV can carry
        """
        model = mobility_models.Lankford_solution

        s = (slope / 360) * (2 * np.pi)  # Convert slope to radians

        # Determine the maximum safe load
        max_load_HPV = min(hpv.load_capacity.flatten()[0], load_attempted)

        # Calculate unloaded velocity
        data_unloaded = (mv.m1, met, s)
        V_guess = 1  # Initial guess for velocity
        V_un = fsolve(model, V_guess, args=data_unloaded, full_output=True)
        unloaded_velocity = V_un[0][0] if V_un[2] == 1 else np.nan

        # Calculate loaded velocity
        total_load = mv.m1 + max_load_HPV
        data_loaded = (total_load, met, s)
        V_load = fsolve(model, V_guess, args=data_loaded, full_output=True)
        loaded_velocity = V_load[0][0] if V_load[2] == 1 else np.nan

        return loaded_velocity, unloaded_velocity, max_load_HPV

    def single_bike_run(mv, mo, hpv, slope, load_attempted):
        model = mobility_models.bike_power_solution

        s = (slope / 360) * (2 * np.pi)  # determine slope in radians

        # determine safe loading for hilly scenarios
        max_load_HPV = max_safe_load(
            hpv.m_HPV_only, hpv.load_capacity, mv.F_max, s, mv.g
        )  # find maximum pushing load
        if max_load_HPV > hpv.load_capacity:
            max_load_HPV = (
                hpv.load_capacity.flatten()
            )  # see if load of HPV or load of pushing is the limitng factor.
        if max_load_HPV > load_attempted:
            max_load_HPV = load_attempted

        data = (
            mv.ro,
            mv.C_d,
            mv.A,
            mv.m1 + hpv.m_HPV_only.flatten(),  #
            hpv.Crr,  # CRR related to the HPV
            mv.eta,
            mv.P_t,
            mv.g,
            s * mo.ulhillpo,  # hill polarity, see model options
        )
        V_guess = 1

        V_un = fsolve(model, V_guess, args=data, full_output=True)
        # checks if the model was sucesful:
        if V_un[2] == 1:
            unloaded_velocity = V_un[0][0]
        else:
            unloaded_velocity = np.nan

        data = (
            mv.ro,
            mv.C_d,
            mv.A,
            mv.m1 + hpv.m_HPV_only.flatten() + max_load_HPV,  #
            hpv.Crr,  # CRR related to the HPV
            mv.eta,
            mv.P_t,
            mv.g,
            s * mo.ulhillpo,  # hill polarity, see model options
        )
        V_guess = 1

        V_load = fsolve(model, V_guess, args=data, full_output=True)
        # checks if the model was sucesful:
        if V_un[2] == 1:
            loaded_velocity = V_load[0][0]
        else:
            loaded_velocity = np.nan

        return loaded_velocity, unloaded_velocity, max_load_HPV


    def numerical_mobility_model(mr, mv, mo, met, hpv):
        """
        1. Takes input of all model variables, mr, mv, mo, met, and hpv
        2. Selects the model to use based on the model options
        3. Creates 3 for loops, looping over 1) HPVs, 2) Slope, 3) load
        4. In the slope loop, determines the slope in radians, then determines the maximum safe load for that slope
        Then, creates a load vector for that partular slope (and that particular HPV), from minimum load to the max safe load
        After that calculates the total load in kg (HPV + pilot + load)
        5. Next, the function calculates the unloaded velocity for the given slope. Note the model options determine the polarity of the slope
        6. Then enters the load loop, which cycles through the recently created load vector
        Now for the ith HPV, the jth slope, and the kth load it will determine the velocity of the HPV given the metabolic/energy input
        Uses scipy.optimize's fsolve to solve the systems of equations int he walking models
        full_output=True means that a flag is returned to see if the solve was succesful.
        Many solves are not successful if the agent 'rus out of energy' and physicaly can't carry the load up the incline with the energy budget provided, these are handled in the if statement using
        """

        limit_practical_load = True

        if mo.model_selection == 1:
            model = mobility_models.bike_power_solution
        elif mo.model_selection == 2:
            model = mobility_models.Lankford_solution
        else:
            print("Unrecognised Model Selection Number")
            exit()

        # start loop iterating over HPVs
        for i, name in enumerate(hpv.name):
            # start loop iterating over slopes
            for j, slope in enumerate(
                mr.slope_vector_deg.reshape(mr.slope_vector_deg.size, 1)
            ):
                s = (slope / 360) * (2 * np.pi)  # determine slope in radians

                # determine safe loading for hilly scenarios
                max_load_HPV = max_safe_load(
                    hpv.m_HPV_only[i], hpv.load_capacity[i], mv.F_max, s, mv.g
                )  # find maximum pushing load
                if max_load_HPV > hpv.load_capacity[i]:
                    max_load_HPV = hpv.load_capacity[
                        i
                    ]  # see if load of HPV or load of pushing is the limitng factor.

                load_vector = linspace_creator(
                    max_load_HPV, mv.minimumViableLoad, mo.load_res
                ).reshape((mo.load_res, 1))

                if limit_practical_load == True:
                    # for all load vector is greater than hpv.practical_limit[i] let = hpv.practical_limit[i]
                    practical_limit = hpv.practical_limit.flatten()[i]
                    load_vector[load_vector > practical_limit] = practical_limit

                m_t = np.array(load_vector + mv.m1 + hpv.m_HPV_only[i])

                ## Determine unloaded velocity of this given slope
                if mo.model_selection == 1:
                    data = (
                        mv.ro,
                        mv.C_d,
                        mv.A,
                        mv.m1 + hpv.m_HPV_only.flatten()[i],  #
                        hpv.Crr.flatten()[i],  # CRR related to the HPV
                        mv.eta,
                        mv.P_t,
                        mv.g,
                        s[0] * mo.ulhillpo,  # hill polarity, see model options
                    )
                    V_guess = 5
                else:
                    data = (
                        mv.m1 + hpv.m_HPV_only.flatten()[i],
                        met,
                        s[0] * mo.ulhillpo,  # hill polarity, see model options
                    )
                    V_guess = 1

                V_un = fsolve(model, V_guess, args=data, full_output=True)
                # checks if the model was sucesful:
                if V_un[2] == 1:
                    mr.v_unload_matrix3d[i, j, :] = V_un[0][0]
                else:
                    mr.v_unload_matrix3d[i, j, :] = np.nan

                # start loop iterating over loads
                for k, total_load in enumerate(m_t.flatten()):
                    if mo.model_selection == 1:
                        data = (
                            mv.ro,
                            mv.C_d,
                            mv.A,
                            total_load,  #
                            hpv.Crr.flatten()[i],  # CRR related to the HPV
                            mv.eta,
                            mv.P_t,
                            mv.g,
                            s[0] * mo.lhillpo,
                        )
                        # V_guess = 12
                    else:
                        data = (total_load, met, s[0])
                        # V_guess = 1

                    V_r = fsolve(model, V_guess, args=data, full_output=True)
                    if V_r[2] == 1:
                        mr.v_load_matrix3d[i, j, k] = V_r[0][0]
                        mr.load_matrix3d[i, j, k] = load_vector[
                            k
                        ]  # amount of water carried
                    else:
                        mr.v_load_matrix3d[i, j, k] = np.nan
                        mr.load_matrix3d[i, j, k] = load_vector[k]

        return mr.v_load_matrix3d, mr.load_matrix3d

    def Lankford_solution(p, *data):
        """
        Lankford model for solving for velocity given a load and slope

        Args:
            p: list of parameters to be solved for
            data: tuple of data to be used in the model
                m_load: mass of the load
                met: metabolic rate of the user
                s: slope
        Returns:
            velocity of the HPV given the load and slope
        """
        m_load, met, s = data
        v_solve = p[0]
        G = (s * 360 / (2 * np.pi)) / 45
        return (
            5.43483
            + (6.47383 * v_solve)
            + (-0.05372 * G)
            + (0.652298 * v_solve * G)
            + (0.023761 * v_solve * G**2)
            + (0.00320 * v_solve * G**3)
            - (met.budget_VO2 / m_load)
        )
        # add in rolling resistance stuff...


class HPV_variables:
    """
    reshapes the incoming dataframe in to the appropriate dimensions for doing numpy maths
    """

    def __init__(self, hpv_param_df, mv):
        self.n_hpv = hpv_param_df.Pilot.size  # number of HPVs
        self.name = np.array(hpv_param_df.Name).reshape((self.n_hpv, 1))[
            :, np.newaxis, :
        ]
        self.m_HPV_only = np.array(hpv_param_df.Weight).reshape((self.n_hpv, 1))[
            :, np.newaxis, :
        ]
        self.n = np.array(hpv_param_df.Efficiency).reshape((self.n_hpv, 1))[
            :, np.newaxis, :
        ]
        self.Crr = np.array(hpv_param_df.Crr).reshape((self.n_hpv, 1))[:, np.newaxis, :]
        self.v_no_load = np.array(hpv_param_df.AverageSpeedWithoutLoad).reshape(
            (self.n_hpv, 1)
        )[:, np.newaxis, :]
        self.load_limit = np.array(hpv_param_df.LoadLimit).reshape((self.n_hpv, 1))[
            :, np.newaxis, :
        ]
        self.practical_limit = np.array(hpv_param_df.PracticalLimit).reshape(
            (self.n_hpv, 1)
        )[:, np.newaxis, :]

        self.Pilot = np.array(hpv_param_df.Pilot).reshape((self.n_hpv, 1))[
            :, np.newaxis, :
        ]

        self.PilotLoad = mv.m1 * self.Pilot

        self.v_no_load = np.array(hpv_param_df.AverageSpeedWithoutLoad).reshape(
            (self.n_hpv, 1)
        )[:, np.newaxis, :]

        self.v_no_load_calculated = 0

        self.GroundContact = np.array(hpv_param_df.GroundContact).reshape(
            (self.n_hpv, 1)
        )[:, np.newaxis, :]

    @property
    def load_capacity(self):
        return self.load_limit - self.PilotLoad


class model_variables:
    def __init__(self):
        #### variables (changeable)
        self.s_deg = 0  # slope in degrees (only used for loading scenario, is overriden in variable slope scenario)
        self.m1 = 62  # mass of rider/person
        self.P_t = 75  # power output of person (steady state average)
        self.F_max = 300  # maximum force exertion for pushing up a hill for a short amount of time
        self.L = 1  # leg length
        self.minimumViableLoad = 0  # in kg, the minimum useful load for such a trip
        self.t_hours = 8  # number of hours to gather water
        self.L = 1  # leg length
        self.A = 0.51  # cross sectional area
        self.C_d = 0.9  # constant for wind
        self.ro = 1.225
        self.eta = 0.92
        self.g = 9.81
        self.waterration = 15


class model_options:
    def __init__(self):
        # model options
        self.model_selection = 2  # 1 is cycling 2 is lankford
        #  0 = min load, 1 = max load, >1 = linear space between min and max
        self.load_res = 15
        #  0 = min slope only, 1 = max slope only, >1 = linear space between min and max
        self.slope_res = 15

        # slope start and end
        self.slope_start = 0  # slope min degrees
        self.slope_end = 10  # slope max degrees

        # is it uphill or downhill? -1 is downhill, +1 is uphill. Any value between 0 to 1 will lesson the impact of the "effective hill", useful for exploring/approximating braking on bikes for donwhill (otherwise we get up to 60km/h on an unloaded bike pleting down a 10 deg hill!)
        self.lhillpo = 1  # loaded hill polarity
        self.ulhillpo = 1  # unloaded hill polarity

        # for plotting of single scenarios, likle on surf plots
        self.slope_scene = (
            0  # 0 is flat ground, -1 will be the steepest hill (slope_end)
        )
        self.load_scene = (
            -1  # 0 is probably 15kg, -1 will be max that the HPV can manage
        )
        self.surf_plot_index = 0  # this one counts the HPVs (as you can only plot one per surf usually, so 0 is the first HPV in the list, -1 will be the last in the list)


        if self.load_res <= 1:
            self.n_load_scenes = 1
        else:
            self.n_load_scenes = self.load_res  # number of load scenarios

    @property
    def model_name(self):
        if self.model_selection == 1:
            return "Cycling"
        elif self.model_selection == 2:
            return "Lankford"
        else:
            return "Unknown"


class MET_values:
    def __init__(self, mv):
        # Metabolic Equivalent of Task
        self.MET_of_sustainable_excercise = (
            4  # # https://en.wikipedia.org/wiki/Metabolic_equivalent_of_task
        )
        self.MET_VO2_conversion = 3.5  # milliliters per minute per kilogram body mass
        self.MET_watt_conversion = 1.162  # watts per kg body mass
        # so 75 Watts output (from Marks textbook) is probably equivalent to about 6 METs
        self.budget_VO2 = (
            self.MET_VO2_conversion * self.MET_of_sustainable_excercise * mv.m1
        )  # vo2 budget for a person
        self.budget_watts = (
            self.MET_watt_conversion * self.MET_of_sustainable_excercise * mv.m1
        )  # vo2 budget for a person


class model_results:
    def __init__(self, hpv, mo):
        self.hpv_name = (hpv.name,)

        # create slope vector
        self.slope_vector_deg = np.array([0, 1, 2, 4.5, 20])

        # = linspace_creator(
        #     np.array([mo.slope_end]), mo.slope_start, mo.slope_res
        # )
        self.slope_vector_deg = self.slope_vector_deg.reshape(
            1, self.slope_vector_deg.size
        )

        # initilise and createoutput 3d matrices (dims: 0 = HPV, 1 = Slope, 2 = load)
        # uses load resolution as a flag, so converts it to "load scenarios", as load_res = 0

        ## initialise matrices
        self.v_load_matrix3d = np.zeros(
            (hpv.n_hpv, self.slope_vector_deg.size, mo.n_load_scenes)
        )
        self.v_unload_matrix3d = np.zeros(
            (hpv.n_hpv, self.slope_vector_deg.size, mo.n_load_scenes)
        )
        self.load_matrix3d = np.zeros(
            (hpv.n_hpv, self.slope_vector_deg.size, mo.n_load_scenes)
        )
        self.slope_matrix3d_deg = np.repeat(self.slope_vector_deg, hpv.n_hpv, axis=0)
        self.slope_matrix3d_deg = np.repeat(
            self.slope_matrix3d_deg[:, :, np.newaxis], mo.n_load_scenes, axis=2
        )
        self.slope_matrix3drads = (self.slope_matrix3d_deg / 360) * (2 * 3.1416)

    def create_dataframe_single_scenario(self, hpv, mv, load_scene, slope_scene):
        df = pd.DataFrame(
            {
                "Name": self.hpv_name[0].transpose()[0][0],
                "Load": self.load_matrix3d[:, slope_scene, load_scene],
                "Slope": self.slope_matrix3d_deg[:, slope_scene, load_scene],
                "Average Trip Velocity": self.v_avg_matrix3d[
                    :, slope_scene, load_scene
                ],
                "Litres * Km": self.distance_achievable_one_hr[
                    :, slope_scene, load_scene
                ]
                * self.load_matrix3d[:, slope_scene, load_scene]
                * mv.t_hours,
                "Water ration * Km": self.distance_achievable_one_hr[
                    :, slope_scene, load_scene
                ]
                * self.load_matrix3d[:, slope_scene, load_scene]
                / mv.waterration
                * mv.t_hours,
                "Distance to Water Achievable": self.distance_achievable_one_hr[
                    :, slope_scene, load_scene
                ]
                * mv.t_hours
                / 2,
                "Total Round trip Distance Achievable": self.distance_achievable_one_hr[
                    :, slope_scene, load_scene
                ]
                * mv.t_hours,
                "Load Velocity [kg * m/s]": self.v_avg_matrix3d[
                    :, slope_scene, load_scene
                ]
                * self.load_matrix3d[:, slope_scene, load_scene],
                "Loaded Velocity": self.v_load_matrix3d[:, slope_scene, load_scene],
                "Unloaded Velocity": hpv.v_no_load.transpose()[0][0],
                "Hours Collecting Water Max": mv.t_hours,
                "Hours Spent Collecting Single Person Water": mv.waterration
                / (
                    self.distance_achievable_one_hr[:, slope_scene, load_scene]
                    * self.load_matrix3d[:, slope_scene, load_scene]
                ),
            }
        )
        return df

    def load_results(self, hpv, mv, mo):
        self.model_name = mo.model_name

        ## Calculate average speed
        # ### CAUTION! this currently uses a hardcoded 'average speed' which is from lit serach, not form the model
        # # Thismight be appropriate, as the model currentl assumes downhill to the water, uphill away, so it is conservative.
        # # average velocity for a round trip
        self.v_avg_matrix3d = (self.v_load_matrix3d + hpv.v_no_load) / 2
        self.v_avg_matrix3d = (self.v_load_matrix3d + self.v_unload_matrix3d) / 2

        self.velocitykgs = self.v_avg_matrix3d * self.load_matrix3d

        # #### Distance
        self.t_secs = mv.t_hours * 60 * 60
        self.distance_achievable = (self.v_avg_matrix3d * self.t_secs) / 1000  # kms
        self.distance_achievable_one_hr = (self.v_avg_matrix3d * 60 * 60) / 1000  # kms

        # power
        self.total_load = self.load_matrix3d + (
            mv.m1 * hpv.Pilot + hpv.m_HPV_only
        )  # total weight when loaded
        # self.Ps = self.v_load_matrix3d * self.total_load * mv.g * np.sin(np.arctan(self.slope_matrix3drads))
        # self.Ps = self.Ps / hpv.n[:, np.newaxis, np.newaxis]


"""
Plotting Class
"""


class plotting_hpv:
    def surf_plot(mr, mo, hpv):
        fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
        # Make data.
        Z = mr.distance_achievable[mo.surf_plot_index, :, :]
        X = mr.load_matrix3d[mo.surf_plot_index, :, :]
        Y = mr.slope_matrix3d_deg[mo.surf_plot_index, :, :]

        # Plot the surface.
        surf = ax.plot_surface(
            X, Y, Z, cmap=cm.coolwarm, linewidth=0, antialiased=False
        )

        # Customize the z axis.
        ax.zaxis.set_major_locator(LinearLocator(10))
        # A StrMethodFormatter is used automatically
        ax.zaxis.set_major_formatter("{x:.02f}")

        ax.set_xlabel("Load [kg]")
        ax.set_ylabel("Slope [deg ˚]")
        ax.set_zlabel("Velocity [m/s]")
        plt.title(
            "Slope, Load & Distance for: " + mr.hpv_name[0][mo.surf_plot_index][0][0]
        )

        plt.show()

    def surf_plotly(mr, mo, hpv):
        # # Make data.
        Z = mr.distance_achievable[mo.surf_plot_index, :, :]
        X = mr.load_matrix3d[mo.surf_plot_index, :, :]
        Y = mr.slope_matrix3d_deg[mo.surf_plot_index, :, :]

        # using the graph options from plotly, create 3d plot.
        fig = go.Figure(data=[go.Surface(z=Z, x=X, y=Y)])
        fig.update_layout(
            title="Slope, Load & Distance for: "
            + mr.hpv_name[0][mo.surf_plot_index][0][0],
            autosize=True,
            width=500,
            height=500,
            margin=dict(l=65, r=50, b=65, t=90),
        )
        fig.show()

    def surf_plotly_multi(mr, mo, hpv):
        plot_height = 700
        plot_width = 900
        xaxis_title = "Load [kg]"
        yaxis_title = "Slope [˚]"
        zaxis_title = "Distannce [km]"
        # create list for plot specs based on number of hpvs
        specs_list = []
        spec_single = [{"type": "surface"}]
        for HPVname in mr.hpv_name:
            specs_list.append(spec_single)

        # create figure and subplots
        fig = make_subplots(
            rows=mr.n_hpv, cols=1, specs=specs_list, subplot_titles=mr.hpv_name
        )  # name the subplots the HPV names (create a new list of strings if you'd like to rename)

        # in a for loop, create the subplots
        mo.surf_plot_index = 0
        for HPVname in mr.hpv_name:
            Z = mr.distance_achievable[mo.surf_plot_index, :, :]
            X = mr.load_matrix3d[mo.surf_plot_index, :, :]
            Y = mr.slope_matrix3d_deg[mo.surf_plot_index, :, :]

            fig.add_trace(
                go.Surface(z=Z, x=X, y=Y, colorscale="Viridis", showscale=False),
                row=1 + mo.surf_plot_index,
                col=1,
            )

            fig.update_scenes(
                xaxis_title_text=xaxis_title,
                yaxis_title_text=yaxis_title,
                zaxis_title_text=zaxis_title,
            )

            mo.surf_plot_index += 1

        # update the layout and create a title for whole thing
        fig.update_layout(
            title_text="3D subplots of HPVs",
            height=plot_height * mr.n_hpv,
            width=plot_width,
        )

        fig.show()

        # show the figure
        # py.iplot(fig, filename="3D subplots of HPVs New")

    def load_plot_plotly(mr, mo, hpv):
        xaxis_title = "Load [kg]"
        yaxis_title = "Speed [m/s]"

        slope_name = mr.slope_vector_deg.flat[mo.slope_scene]
        chart_title = "m/s with different loads, Constant %0.1f slope, model %s" % (
            slope_name,
            mr.model_name,
        )

        i = 0

        fig = go.Figure()
        for HPVname in mr.hpv_name[0].transpose()[0][0]:
            y = mr.v_load_matrix3d[i, mo.slope_scene, :]
            x = mr.load_matrix3d[i, mo.slope_scene, :]
            i += 1
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=HPVname))

        # Update the title
        fig.update_layout(title=dict(text=chart_title))
        # Update te axis label (valid for 2d graphs using graph object)
        fig.update_xaxes(title_text=xaxis_title)
        fig.update_yaxes(title_text=yaxis_title)
        # fig.update_yaxes(range = [2,5.5])

        fig.show()
        # py.iplot(fig, filename=chart_title)

    def slope_plot_plotly(mr, mo, hpv):
        xaxis_title = "Slope [˚]"
        yaxis_title = "m/s"
        if mo.load_scene == 0:
            load_name = mr.load_matrix3d.flat[mo.load_scene]
        elif mo.load_scene == -1:
            load_name = "maximum"
        else:
            load_name = "variable"

        chart_title = (
            f"m/s with different slope, {load_name} kg load, model {mr.model_name}"
        )

        i = 0
        fig = go.Figure()
        for HPVname in mr.hpv_name[0].transpose()[0][0]:
            # y = mr.velocitykgs[
            y = mr.v_load_matrix3d[
                i, :, mo.load_scene
            ]  # SEE ZEROS <-- this is for the minimum weight
            x = mr.slope_matrix3d_deg[i, :, mo.load_scene]
            i += 1
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=HPVname))

        # Update the title
        fig.update_layout(title=dict(text=chart_title))
        # Update te axis label (valid for 2d graphs using graph object)
        fig.update_xaxes(title_text=xaxis_title)
        fig.update_yaxes(title_text=yaxis_title)
        # fig.update_yaxes(range=[0, 15])

        fig.show()
        # py.iplot(fig, filename=chart_title)

    def slope_velcoity_kgs(mr, mo, hpv):
        xaxis_title = "Slope [˚]"
        yaxis_title = "Velocity Kgs"

        if mo.load_scene == 0:
            load_name = mr.load_matrix3d.flat[mo.load_scene]
        elif mo.load_scene == -1:
            load_name = "maximum"
        else:
            load_name = "variable"

        chart_title = f"Velocity Kgs with different slope, {load_name} kg load, model {mr.model_name}"

        i = 0

        fig = go.Figure()
        for HPVname in mr.hpv_name[0].transpose()[0][0]:
            # y = mr.velocitykgs[
            y = mr.velocitykgs[
                i, :, mo.load_scene
            ]  # SEE ZEROS <-- this is for the minimum weight
            x = mr.slope_matrix3d_deg[i, :, mo.load_scene]
            i += 1
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=HPVname))

        # Update the title
        fig.update_layout(title=dict(text=chart_title))
        # Update te axis label (valid for 2d graphs using graph object)
        fig.update_xaxes(title_text=xaxis_title)
        fig.update_yaxes(title_text=yaxis_title)
        # fig.update_yaxes(range=[0, 15])

        fig.show()
        # py.iplot(fig, filename=chart_title)

    def slope_velocities(mr, mo, hpv):
        HPV = 0

        xaxis_title = "Slope [˚]"
        yaxis_title = "Velocity [m/s]"
        load_name = mr.load_matrix3d[HPV][0][mo.load_scene]

        chart_title = f"m/s with different slope, {load_name} kg load,\n for HPV: {hpv.name.flatten()[0]}, model {mr.model_name}"

        fig = go.Figure()
        x = mr.slope_matrix3d_deg[HPV, :, mo.load_scene]
        y = mr.v_avg_matrix3d[HPV, :, mo.load_scene]
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name="Average"))
        y = mr.v_load_matrix3d[HPV, :, mo.load_scene]
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name="Loaded"))
        y = mr.v_unload_matrix3d[HPV, :, mo.load_scene]
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name="Unloaded"))

        # Update the title
        fig.update_layout(title=dict(text=chart_title))
        # Update te axis label (valid for 2d graphs using graph object)
        fig.update_xaxes(title_text=xaxis_title)
        fig.update_yaxes(title_text=yaxis_title)
        # fig.update_yaxes(range=[0, 15])

        fig.show()
        # py.iplot(fig, filename=chart_title)

    def time_sensitivity_plotly_grouped(mr, mo, hpv):
        t_hours_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        load_scene = -1

        # plotly setup
        fig = go.Figure()
        i = 0
        # add trace for eat
        for HPVname in mr.hpv_name[0].transpose()[0][0]:
            X = t_hours_list
            Y = mr.load_matrix3d[i, 0, load_scene] * (
                mr.distance_achievable_one_hr[i, 0, load_scene] * np.array(t_hours_list)
            )
            fig.add_trace(go.Bar(x=X, y=Y, name=HPVname))
            i += 1

        fig.update_layout(
            title=dict(
                text="Distance Achievable Per HPV given different time to collect water"
            )
        )
        fig.update_layout(barmode="group")
        fig.show()

    def bar_plot_loading(mr, mo, hpv, mv):
        t_hours_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

        slope_name = mr.slope_vector_deg.flat[mo.slope_scene]
        chart_title = "Efficiency at %0.2f degrees" % slope_name

        df = mr.create_dataframe_single_scenario(hpv, mv, mo.load_scene, mo.slope_scene)

        fig = px.bar(
            df,
            x="Load",
            y="Load Velocity [kg * m/s]",
            hover_data=[
                "Name",
                "Average Trip Velocity",
                "Loaded Velocity",
                "Unloaded Velocity",
                "Distance to Water Achievable",
                "Total Round trip Distance Achievable",
                "Load",
                "Slope",
                "Hours Collecting Water Max",
                "Hours Spent Collecting Single Person Water",
            ],
            color="Name",
            labels={"Name": "Name"},
            title=chart_title,
        )
        fig.show()
        # py.iplot(fig, filename=chart_title)

    def bar_plot_loading_distance(mr, mo, hpv, mv):
        slope_name = mr.slope_vector_deg.flat[mo.slope_scene]
        chart_title = "Efficiency at %0.2f degrees, with model %s" % (
            slope_name,
            mr.model_name,
        )

        df = mr.create_dataframe_single_scenario(hpv, mv, mo.load_scene, mo.slope_scene)

        fig = px.bar(
            df,
            x="Load",
            y="Water ration * Km",
            hover_data=[
                "Name",
                "Average Trip Velocity",
                "Loaded Velocity",
                "Unloaded Velocity",
                "Distance to Water Achievable",
                "Total Round trip Distance Achievable",
                "Load",
                "Slope",
                "Hours Collecting Water Max",
                "Hours Spent Collecting Single Person Water",
            ],
            color="Name",
            labels={"Name": "Name"},
            title=chart_title,
        )
        fig.show()
        # py.iplot(fig, filename=chart_title)


if __name__ == "__main__":
    # mr = ModelResults()
    ######################
    #### Import Data #####

    file_path_params = "../data/lookup tables/mobility-model-parameters.csv"
    param_df = pd.read_csv(file_path_params)

    mo = model_options()
    mv = model_variables()
    hpv = HPV_variables(param_df, mv)
    V_guess = 12
    s = [0]
    i = 0

    data = (
        mv.ro,
        mv.C_d,
        mv.A,
        mv.m1 + hpv.m_HPV_only.flatten()[i],  #
        hpv.Crr.flatten()[i],  # CRR related to the HPV
        mv.eta,
        mv.P_t,
        mv.g,
        s[0] * mo.ulhillpo,  # hill polarity, see model options
    )

    model = mobility_models.bike_power_solution
    V_r = fsolve(model, V_guess, args=data, full_output=True)
