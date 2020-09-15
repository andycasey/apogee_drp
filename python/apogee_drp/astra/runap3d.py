import luigi
import os
import subprocess
import glob
import pickle
from astra.tasks import BaseTask
from astra.tasks.io import ApPlanFile # This task does not exist yet!
from sdss import yanny

from luigi.util import inherits

# Inherit the parameters needed to define an ApPlanFile, since we will need these to
# require() the correct ApPlanFile.
@inherits(ApPlanFile)
class RunAP3D(BaseTask):

    def requires(self):
        # We require plan files to exist!
        return ApPlanFile(**self.get_common_param_kwargs(ApPlanFile))

    def output(self):
        # Store the 2D images in the same directory as the plan file.
        output_path_prefix, ext = os.path.splitext(self.input().path)
        return luigi.LocalTarget(f"{output_path_prefix}-done")

    def run(self):
        # Run the IDL program!
        subprocess.call(["idl","-e","ap3d,",self.input().path])

        # Load the plan file
        # (Note: I'd suggest moving all yanny files to YAML format and/or just supply the plan file
        # inputs as variables to the task.)
        plan = yanny.yanny(self.input().path)
        exposures = plan['EXPOSURES']

        # Check that the three ap2D files were created
        counter = 0
        for exp in exposures:
            files = self.output().path+"ap2D-*-"+str(exp)+".fits"
            check = glob.glob(files)
            if len(check) == 3: 
                counter += 1

        # Create "done" file if 2D frames exist
        if counter == len(exposures):
            with open(self.output().path, "w") as fp:
                fp.write(" ")



if __name__ == "__main__":

    # The parameters for RunAP3D are the same as those needed to identify the ApPlanFile:
    # From the path definition at:
    #   https://sdss-access.readthedocs.io/en/latest/path_defs.html#dr16

    # We can see that the following parameters are needed:
    #   $APOGEE_REDUX/{apred}/visit/{telescope}/{field}/{plate}/{mjd}/{prefix}Plan-{plate}-{mjd}.par

    # Define the task.
    # (Note these are not real numbers I am making them up.)
    task = RunAP3D(
        apred="r12",
        telescope="apo25m",
        field="139+00",
        mjd="324239",
        prefix="ap"
    )

    # (At least) Two ways to run this:
    # Option 1: useful for interactive debugging with %debug
    task.run()


    # Option 2: Use Luigi to build the dependency graph. Useful if you have a complex workflow, but
    #           bad if you want to interactively debug (because it doesn't allow it).
    luigi.build(
        [task],
        local_scheduler=True
    )

    # Option 3: Use a command line tool to run this specific task.
    # Option 4: Use a command line tool and an already-running scheduler to execute the task, and
    #           then see the progress in a web browser.